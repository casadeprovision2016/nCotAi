/*!
COTAI Security Service
High-performance security modules written in Rust for critical security operations
*/

use actix_web::{web, App, HttpServer, HttpResponse, Result, middleware::Logger};
use actix_cors::Cors;
use tracing::{info, error};
use tracing_subscriber;

mod config;
mod crypto;
mod auth;
mod audit;
mod monitoring;
mod rate_limiting;
mod validation;
mod storage;
mod errors;

use config::Config;
use crypto::CryptoService;
use auth::AuthService;
use audit::AuditService;
use monitoring::MetricsService;
use rate_limiting::RateLimiter;

pub struct AppState {
    pub config: Config,
    pub crypto_service: CryptoService,
    pub auth_service: AuthService,
    pub audit_service: AuditService,
    pub metrics_service: MetricsService,
    pub rate_limiter: RateLimiter,
}

async fn health_check() -> Result<HttpResponse> {
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "cotai-security",
        "version": "1.0.0"
    })))
}

async fn readiness_check(data: web::Data<AppState>) -> Result<HttpResponse> {
    // Check all critical services
    let mut checks = Vec::new();
    
    // Check crypto service
    if data.crypto_service.is_ready().await {
        checks.push(("crypto", "ready"));
    } else {
        checks.push(("crypto", "not_ready"));
    }
    
    // Check auth service
    if data.auth_service.is_ready().await {
        checks.push(("auth", "ready"));
    } else {
        checks.push(("auth", "not_ready"));
    }
    
    // Check audit service
    if data.audit_service.is_ready().await {
        checks.push(("audit", "ready"));
    } else {
        checks.push(("audit", "not_ready"));
    }
    
    let all_ready = checks.iter().all(|(_, status)| *status == "ready");
    
    if all_ready {
        Ok(HttpResponse::Ok().json(serde_json::json!({
            "status": "ready",
            "checks": checks
        })))
    } else {
        Ok(HttpResponse::ServiceUnavailable().json(serde_json::json!({
            "status": "not_ready",
            "checks": checks
        })))
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    info!("Starting COTAI Security Service");

    // Load configuration
    let config = Config::from_env().expect("Failed to load configuration");
    let bind_addr = format!("{}:{}", config.host, config.port);

    // Initialize services
    let crypto_service = CryptoService::new(&config).await
        .expect("Failed to initialize crypto service");
    
    let auth_service = AuthService::new(&config).await
        .expect("Failed to initialize auth service");
    
    let audit_service = AuditService::new(&config).await
        .expect("Failed to initialize audit service");
    
    let metrics_service = MetricsService::new(&config).await
        .expect("Failed to initialize metrics service");
    
    let rate_limiter = RateLimiter::new(&config)
        .expect("Failed to initialize rate limiter");

    // Create application state
    let app_state = web::Data::new(AppState {
        config: config.clone(),
        crypto_service,
        auth_service,
        audit_service,
        metrics_service,
        rate_limiter,
    });

    info!("Security service starting on {}", bind_addr);

    // Start HTTP server
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(Logger::default())
            .wrap(
                Cors::default()
                    .allowed_origin_fn(|origin, _req_head| {
                        origin.as_bytes().starts_with(b"https://")
                    })
                    .allowed_methods(vec!["GET", "POST", "PUT", "DELETE"])
                    .allowed_headers(vec!["Authorization", "Content-Type"])
                    .max_age(3600)
            )
            .route("/health", web::get().to(health_check))
            .route("/ready", web::get().to(readiness_check))
            .service(
                web::scope("/api/v1")
                    .configure(crypto::configure_routes)
                    .configure(auth::configure_routes)
                    .configure(audit::configure_routes)
                    .configure(monitoring::configure_routes)
            )
    })
    .bind(&bind_addr)?
    .run()
    .await
}