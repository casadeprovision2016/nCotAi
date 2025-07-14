package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"cotai-pdf-processor/internal/api"
	"cotai-pdf-processor/internal/config"
	"cotai-pdf-processor/internal/processor"
	"cotai-pdf-processor/internal/storage"
	"cotai-pdf-processor/internal/telemetry"

	"github.com/gin-gonic/gin"
)

func main() {
	// Load configuration
	cfg := config.Load()

	// Initialize telemetry
	tracer, err := telemetry.InitTracer(cfg.ServiceName)
	if err != nil {
		log.Fatalf("Failed to initialize tracer: %v", err)
	}

	// Initialize storage connections
	redis := storage.NewRedisClient(cfg.RedisURL)
	defer redis.Close()

	postgres := storage.NewPostgresClient(cfg.DatabaseURL)
	defer postgres.Close()

	// Initialize PDF processor
	pdfProcessor := processor.NewPDFProcessor(redis, postgres, tracer)

	// Start worker pool
	workerPool := processor.NewWorkerPool(cfg.WorkerCount, pdfProcessor)
	workerPool.Start()
	defer workerPool.Stop()

	// Setup HTTP server
	router := gin.Default()
	api.SetupRoutes(router, pdfProcessor, workerPool)

	server := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: router,
	}

	// Start server
	go func() {
		log.Printf("PDF Processor service starting on port %s", cfg.Port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited")
}