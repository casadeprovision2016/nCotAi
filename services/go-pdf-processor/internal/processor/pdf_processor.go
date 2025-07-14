package processor

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strings"
	"time"

	"cotai-pdf-processor/internal/storage"

	"github.com/ledongthuc/pdf"
	"github.com/otiai10/gosseract/v2"
	"go.opentelemetry.io/otel/trace"
)

type PDFProcessor struct {
	redis    *storage.RedisClient
	postgres *storage.PostgresClient
	tracer   trace.Tracer
}

type ProcessingJob struct {
	ID          string                 `json:"id"`
	FileURL     string                 `json:"file_url"`
	TenderID    string                 `json:"tender_id"`
	UserID      string                 `json:"user_id"`
	Options     ProcessingOptions      `json:"options"`
	Status      string                 `json:"status"`
	CreatedAt   time.Time              `json:"created_at"`
	StartedAt   *time.Time             `json:"started_at,omitempty"`
	CompletedAt *time.Time             `json:"completed_at,omitempty"`
	Result      *ProcessingResult      `json:"result,omitempty"`
	Error       string                 `json:"error,omitempty"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type ProcessingOptions struct {
	EnableOCR        bool     `json:"enable_ocr"`
	Languages        []string `json:"languages"`
	ExtractEntities  bool     `json:"extract_entities"`
	AnalyzeRisks     bool     `json:"analyze_risks"`
	GenerateScore    bool     `json:"generate_score"`
	MaxPages         int      `json:"max_pages"`
	DPI              int      `json:"dpi"`
}

type ProcessingResult struct {
	ExtractedText   string                 `json:"extracted_text"`
	PageCount       int                    `json:"page_count"`
	FileSize        int64                  `json:"file_size"`
	ProcessingTime  time.Duration          `json:"processing_time"`
	Entities        []ExtractedEntity      `json:"entities"`
	RiskAnalysis    RiskAnalysis           `json:"risk_analysis"`
	RelevanceScore  float64                `json:"relevance_score"`
	QualityMetrics  QualityMetrics         `json:"quality_metrics"`
	Metadata        map[string]interface{} `json:"metadata"`
}

type ExtractedEntity struct {
	Type       string  `json:"type"`
	Value      string  `json:"value"`
	Confidence float64 `json:"confidence"`
	StartPos   int     `json:"start_pos"`
	EndPos     int     `json:"end_pos"`
	Page       int     `json:"page"`
}

type RiskAnalysis struct {
	OverallRisk     string             `json:"overall_risk"`
	RiskScore       float64            `json:"risk_score"`
	IdentifiedRisks []IdentifiedRisk   `json:"identified_risks"`
	Recommendations []string           `json:"recommendations"`
	Confidence      float64            `json:"confidence"`
}

type IdentifiedRisk struct {
	Category    string  `json:"category"`
	Description string  `json:"description"`
	Severity    string  `json:"severity"`
	Impact      string  `json:"impact"`
	Confidence  float64 `json:"confidence"`
	Location    string  `json:"location"`
}

type QualityMetrics struct {
	TextQuality    float64 `json:"text_quality"`
	OCRConfidence  float64 `json:"ocr_confidence"`
	DocumentClarity float64 `json:"document_clarity"`
	Completeness   float64 `json:"completeness"`
	Readability    float64 `json:"readability"`
}

func NewPDFProcessor(redis *storage.RedisClient, postgres *storage.PostgresClient, tracer trace.Tracer) *PDFProcessor {
	return &PDFProcessor{
		redis:    redis,
		postgres: postgres,
		tracer:   tracer,
	}
}

func (p *PDFProcessor) ProcessDocument(ctx context.Context, job *ProcessingJob) error {
	ctx, span := p.tracer.Start(ctx, "process_document")
	defer span.End()

	startTime := time.Now()
	job.StartedAt = &startTime
	job.Status = "processing"

	// Update job status in Redis
	if err := p.updateJobStatus(ctx, job); err != nil {
		log.Printf("Failed to update job status: %v", err)
	}

	// Download and process the file
	result, err := p.processFile(ctx, job)
	if err != nil {
		job.Status = "failed"
		job.Error = err.Error()
		p.updateJobStatus(ctx, job)
		return fmt.Errorf("failed to process file: %w", err)
	}

	// Calculate processing time
	completedAt := time.Now()
	result.ProcessingTime = completedAt.Sub(startTime)
	job.CompletedAt = &completedAt
	job.Result = result
	job.Status = "completed"

	// Update final status
	if err := p.updateJobStatus(ctx, job); err != nil {
		log.Printf("Failed to update final job status: %v", err)
	}

	// Store results in database
	if err := p.storeResults(ctx, job); err != nil {
		log.Printf("Failed to store results: %v", err)
	}

	// Trigger AI analysis if requested
	if job.Options.ExtractEntities || job.Options.AnalyzeRisks || job.Options.GenerateScore {
		go p.triggerAIAnalysis(context.Background(), job)
	}

	return nil
}

func (p *PDFProcessor) processFile(ctx context.Context, job *ProcessingJob) (*ProcessingResult, error) {
	ctx, span := p.tracer.Start(ctx, "process_file")
	defer span.End()

	// Download file (simplified - in real implementation, download from URL)
	// For now, assume we have the file path
	filePath := job.FileURL

	result := &ProcessingResult{
		QualityMetrics: QualityMetrics{},
		Entities:       []ExtractedEntity{},
		Metadata:       make(map[string]interface{}),
	}

	// Extract text from PDF
	text, pageCount, err := p.extractTextFromPDF(ctx, filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to extract text: %w", err)
	}

	result.ExtractedText = text
	result.PageCount = pageCount

	// OCR processing if enabled and text is insufficient
	if job.Options.EnableOCR && (len(text) < 100 || p.hasLowTextQuality(text)) {
		ocrText, confidence, err := p.performOCR(ctx, filePath, job.Options)
		if err != nil {
			log.Printf("OCR failed: %v", err)
		} else {
			result.ExtractedText = p.combineTexts(text, ocrText)
			result.QualityMetrics.OCRConfidence = confidence
		}
	}

	// Calculate quality metrics
	result.QualityMetrics = p.calculateQualityMetrics(result.ExtractedText, result.PageCount)

	// Basic entity extraction (simplified)
	if job.Options.ExtractEntities {
		result.Entities = p.extractBasicEntities(result.ExtractedText)
	}

	// Basic risk analysis (simplified)
	if job.Options.AnalyzeRisks {
		result.RiskAnalysis = p.performBasicRiskAnalysis(result.ExtractedText)
	}

	// Generate relevance score
	if job.Options.GenerateScore {
		result.RelevanceScore = p.generateRelevanceScore(result.ExtractedText, job.Metadata)
	}

	return result, nil
}

func (p *PDFProcessor) extractTextFromPDF(ctx context.Context, filePath string) (string, int, error) {
	ctx, span := p.tracer.Start(ctx, "extract_text_pdf")
	defer span.End()

	// Open PDF file
	file, reader, err := pdf.Open(filePath)
	if err != nil {
		return "", 0, fmt.Errorf("failed to open PDF: %w", err)
	}
	defer file.Close()

	var textBuilder strings.Builder
	pageCount := reader.NumPage()

	// Extract text from each page
	for i := 1; i <= pageCount; i++ {
		page := reader.Page(i)
		if page.V.IsNull() {
			continue
		}

		text, err := page.GetPlainText(nil)
		if err != nil {
			log.Printf("Failed to extract text from page %d: %v", i, err)
			continue
		}

		textBuilder.WriteString(text)
		textBuilder.WriteString("\n")
	}

	return textBuilder.String(), pageCount, nil
}

func (p *PDFProcessor) performOCR(ctx context.Context, filePath string, options ProcessingOptions) (string, float64, error) {
	ctx, span := p.tracer.Start(ctx, "perform_ocr")
	defer span.End()

	client := gosseract.NewClient()
	defer client.Close()

	// Set languages
	if len(options.Languages) > 0 {
		client.SetLanguage(strings.Join(options.Languages, "+"))
	} else {
		client.SetLanguage("por+eng") // Portuguese and English by default
	}

	// Configure OCR settings for better accuracy
	client.SetPageSegMode(gosseract.PSM_AUTO)
	client.SetConfigFile("pdf")
	
	// Set DPI if specified
	if options.DPI > 0 {
		client.SetVariable("tessedit_pageseg_mode", fmt.Sprintf("%d", options.DPI))
	}

	// Set image source
	client.SetImage(filePath)

	// Get text
	text, err := client.Text()
	if err != nil {
		return "", 0, fmt.Errorf("OCR failed: %w", err)
	}

	// Get confidence score
	confidence := 85.0 // Default confidence
	if confidenceStr, err := client.GetMeanConfidence(); err == nil {
		if conf, parseErr := fmt.Sscanf(confidenceStr, "%f", &confidence); parseErr == nil && conf == 1 {
			// Successfully parsed confidence
		}
	}

	return text, confidence, nil
}

func (p *PDFProcessor) hasLowTextQuality(text string) bool {
	// Simple heuristic to determine if text quality is low
	if len(text) < 100 {
		return true
	}

	// Check for unusual character patterns that might indicate OCR issues
	specialChars := strings.Count(text, "□") + strings.Count(text, "◯") + strings.Count(text, "●")
	return float64(specialChars)/float64(len(text)) > 0.1
}

func (p *PDFProcessor) combineTexts(originalText, ocrText string) string {
	// Simple text combination logic
	if len(originalText) > len(ocrText) {
		return originalText
	}
	return ocrText
}

func (p *PDFProcessor) calculateQualityMetrics(text string, pageCount int) QualityMetrics {
	textLength := len(text)
	
	// Simple quality calculations
	textQuality := float64(textLength) / float64(pageCount*500) // Assume 500 chars per page is good
	if textQuality > 1.0 {
		textQuality = 1.0
	}

	return QualityMetrics{
		TextQuality:     textQuality,
		OCRConfidence:   0.85, // Default
		DocumentClarity: 0.80, // Default
		Completeness:    textQuality,
		Readability:     0.75, // Default
	}
}

func (p *PDFProcessor) extractBasicEntities(text string) []ExtractedEntity {
	entities := []ExtractedEntity{}

	// Simple entity extraction patterns
	patterns := map[string]string{
		"CNPJ":      `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`,
		"CPF":       `\d{3}\.\d{3}\.\d{3}-\d{2}`,
		"EMAIL":     `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`,
		"PHONE":     `\(\d{2}\)\s*\d{4,5}-\d{4}`,
		"CURRENCY":  `R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?`,
		"DATE":      `\d{1,2}/\d{1,2}/\d{4}`,
	}

	// This is a simplified implementation
	// In production, use proper regex and NLP libraries
	for entityType, pattern := range patterns {
		if strings.Contains(text, "CNPJ") && entityType == "CNPJ" {
			entities = append(entities, ExtractedEntity{
				Type:       entityType,
				Value:      "XX.XXX.XXX/XXXX-XX", // Placeholder
				Confidence: 0.85,
				StartPos:   0,
				EndPos:     20,
				Page:       1,
			})
		}
	}

	return entities
}

func (p *PDFProcessor) performBasicRiskAnalysis(text string) RiskAnalysis {
	risks := []IdentifiedRisk{}
	riskScore := 0.0

	// Simple risk detection
	riskKeywords := map[string]float64{
		"multa":           0.3,
		"penalidade":      0.4,
		"rescisão":        0.5,
		"garantia":        0.2,
		"caução":          0.3,
		"prazo":           0.1,
		"inexequível":     0.8,
		"impugnação":      0.6,
		"exclusivo":       0.4,
	}

	textLower := strings.ToLower(text)
	for keyword, weight := range riskKeywords {
		if strings.Contains(textLower, keyword) {
			riskScore += weight
			risks = append(risks, IdentifiedRisk{
				Category:    "contractual",
				Description: fmt.Sprintf("Detected keyword: %s", keyword),
				Severity:    "medium",
				Impact:      "financial",
				Confidence:  0.7,
				Location:    "document",
			})
		}
	}

	// Normalize risk score
	if riskScore > 1.0 {
		riskScore = 1.0
	}

	overallRisk := "low"
	if riskScore > 0.7 {
		overallRisk = "high"
	} else if riskScore > 0.4 {
		overallRisk = "medium"
	}

	return RiskAnalysis{
		OverallRisk:     overallRisk,
		RiskScore:       riskScore,
		IdentifiedRisks: risks,
		Recommendations: []string{"Review contract terms carefully", "Consult legal team"},
		Confidence:      0.75,
	}
}

func (p *PDFProcessor) generateRelevanceScore(text string, metadata map[string]interface{}) float64 {
	// Simple relevance scoring
	score := 0.5 // Base score

	// Check for relevant keywords
	relevantKeywords := []string{
		"licitação", "pregão", "concorrência", "convite",
		"serviços", "fornecimento", "obras", "compras",
	}

	textLower := strings.ToLower(text)
	for _, keyword := range relevantKeywords {
		if strings.Contains(textLower, keyword) {
			score += 0.1
		}
	}

	if score > 1.0 {
		score = 1.0
	}

	return score
}

func (p *PDFProcessor) updateJobStatus(ctx context.Context, job *ProcessingJob) error {
	jobData, err := json.Marshal(job)
	if err != nil {
		return err
	}

	return p.redis.Set(ctx, fmt.Sprintf("job:%s", job.ID), jobData, 24*time.Hour)
}

func (p *PDFProcessor) storeResults(ctx context.Context, job *ProcessingJob) error {
	// Store in PostgreSQL (simplified)
	query := `
		INSERT INTO processing_jobs (id, tender_id, user_id, status, result, created_at, completed_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (id) DO UPDATE SET
			status = EXCLUDED.status,
			result = EXCLUDED.result,
			completed_at = EXCLUDED.completed_at
	`

	resultJSON, _ := json.Marshal(job.Result)
	
	return p.postgres.Exec(ctx, query,
		job.ID, job.TenderID, job.UserID, job.Status,
		resultJSON, job.CreatedAt, job.CompletedAt)
}

func (p *PDFProcessor) triggerAIAnalysis(ctx context.Context, job *ProcessingJob) {
	// Trigger advanced AI analysis service
	// This would call the AI engine service
	log.Printf("Triggering AI analysis for job %s", job.ID)
}