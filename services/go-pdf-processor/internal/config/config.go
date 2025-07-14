package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type Config struct {
	ServiceName  string
	Port         string
	RedisURL     string
	DatabaseURL  string
	WorkerCount  int
	JaegerURL    string
	MaxFileSize  int64
	AllowedTypes []string
}

func Load() *Config {
	// Load .env file if exists
	godotenv.Load()

	workerCount, _ := strconv.Atoi(getEnv("WORKER_COUNT", "10"))
	maxFileSize, _ := strconv.ParseInt(getEnv("MAX_FILE_SIZE", "52428800"), 10, 64) // 50MB default

	return &Config{
		ServiceName:  getEnv("SERVICE_NAME", "cotai-pdf-processor"),
		Port:         getEnv("PORT", "8080"),
		RedisURL:     getEnv("REDIS_URL", "redis://localhost:6379"),
		DatabaseURL:  getEnv("DATABASE_URL", "postgres://user:password@localhost/cotai?sslmode=disable"),
		WorkerCount:  workerCount,
		JaegerURL:    getEnv("JAEGER_URL", "http://localhost:14268/api/traces"),
		MaxFileSize:  maxFileSize,
		AllowedTypes: []string{"application/pdf", "image/png", "image/jpeg", "image/tiff"},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}