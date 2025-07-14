package processor

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

	"golang.org/x/sync/semaphore"
)

type WorkerPool struct {
	workers     int
	processor   *PDFProcessor
	jobQueue    chan *ProcessingJob
	quit        chan bool
	wg          sync.WaitGroup
	semaphore   *semaphore.Weighted
	active      bool
	mu          sync.RWMutex
}

type PoolStats struct {
	TotalWorkers    int       `json:"total_workers"`
	ActiveJobs      int       `json:"active_jobs"`
	QueuedJobs      int       `json:"queued_jobs"`
	ProcessedJobs   int64     `json:"processed_jobs"`
	FailedJobs      int64     `json:"failed_jobs"`
	AverageTime     float64   `json:"average_processing_time"`
	LastProcessed   time.Time `json:"last_processed"`
}

func NewWorkerPool(workers int, processor *PDFProcessor) *WorkerPool {
	return &WorkerPool{
		workers:   workers,
		processor: processor,
		jobQueue:  make(chan *ProcessingJob, workers*2), // Buffer size
		quit:      make(chan bool),
		semaphore: semaphore.NewWeighted(int64(workers)),
	}
}

func (wp *WorkerPool) Start() {
	wp.mu.Lock()
	defer wp.mu.Unlock()

	if wp.active {
		return
	}

	wp.active = true
	
	// Start worker goroutines
	for i := 0; i < wp.workers; i++ {
		wp.wg.Add(1)
		go wp.worker(i)
	}

	log.Printf("Worker pool started with %d workers", wp.workers)
}

func (wp *WorkerPool) Stop() {
	wp.mu.Lock()
	defer wp.mu.Unlock()

	if !wp.active {
		return
	}

	wp.active = false
	close(wp.quit)
	wp.wg.Wait()
	close(wp.jobQueue)
	
	log.Println("Worker pool stopped")
}

func (wp *WorkerPool) SubmitJob(job *ProcessingJob) error {
	wp.mu.RLock()
	defer wp.mu.RUnlock()

	if !wp.active {
		return ErrPoolClosed
	}

	select {
	case wp.jobQueue <- job:
		log.Printf("Job %s queued for processing", job.ID)
		return nil
	default:
		return ErrQueueFull
	}
}

func (wp *WorkerPool) worker(id int) {
	defer wp.wg.Done()
	
	log.Printf("Worker %d started", id)
	
	for {
		select {
		case job := <-wp.jobQueue:
			if job == nil {
				log.Printf("Worker %d: received nil job, stopping", id)
				return
			}
			
			wp.processJob(id, job)
			
		case <-wp.quit:
			log.Printf("Worker %d stopping", id)
			return
		}
	}
}

func (wp *WorkerPool) processJob(workerID int, job *ProcessingJob) {
	startTime := time.Now()
	
	// Acquire semaphore
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	
	if err := wp.semaphore.Acquire(ctx, 1); err != nil {
		log.Printf("Worker %d: failed to acquire semaphore: %v", workerID, err)
		wp.markJobFailed(job, err)
		return
	}
	defer wp.semaphore.Release(1)
	
	log.Printf("Worker %d: processing job %s", workerID, job.ID)
	
	// Process the job
	if err := wp.processor.ProcessDocument(ctx, job); err != nil {
		log.Printf("Worker %d: job %s failed: %v", workerID, job.ID, err)
		wp.markJobFailed(job, err)
	} else {
		duration := time.Since(startTime)
		log.Printf("Worker %d: job %s completed in %v", workerID, job.ID, duration)
	}
}

func (wp *WorkerPool) markJobFailed(job *ProcessingJob, err error) {
	job.Status = "failed"
	job.Error = err.Error()
	now := time.Now()
	job.CompletedAt = &now
	
	// Update job status in storage
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	if updateErr := wp.processor.updateJobStatus(ctx, job); updateErr != nil {
		log.Printf("Failed to update failed job status: %v", updateErr)
	}
}

func (wp *WorkerPool) GetStats() PoolStats {
	wp.mu.RLock()
	defer wp.mu.RUnlock()
	
	return PoolStats{
		TotalWorkers: wp.workers,
		ActiveJobs:   int(wp.workers) - int(wp.semaphore.TryAcquire(int64(wp.workers))),
		QueuedJobs:   len(wp.jobQueue),
		// Additional stats would be tracked in a real implementation
	}
}

func (wp *WorkerPool) IsActive() bool {
	wp.mu.RLock()
	defer wp.mu.RUnlock()
	return wp.active
}

// Health check for the worker pool
func (wp *WorkerPool) HealthCheck() error {
	wp.mu.RLock()
	defer wp.mu.RUnlock()
	
	if !wp.active {
		return ErrPoolClosed
	}
	
	// Check if workers are responsive
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	// Try to acquire and immediately release a semaphore slot
	if err := wp.semaphore.Acquire(ctx, 1); err != nil {
		return ErrPoolOverloaded
	}
	wp.semaphore.Release(1)
	
	return nil
}

// Custom errors
var (
	ErrPoolClosed     = &PoolError{"worker pool is closed"}
	ErrQueueFull      = &PoolError{"job queue is full"}
	ErrPoolOverloaded = &PoolError{"worker pool is overloaded"}
)

type PoolError struct {
	msg string
}

func (e *PoolError) Error() string {
	return e.msg
}