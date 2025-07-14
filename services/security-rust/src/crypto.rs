/*!
Cryptographic Security Module
High-performance cryptographic operations for sensitive data protection
*/

use actix_web::{web, HttpResponse, Result};
use ring::{
    aead::{Aad, LessSafeKey, Nonce, UnboundKey, AES_256_GCM},
    rand::{SecureRandom, SystemRandom},
    digest::{Context, Digest, SHA256},
    hmac,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{info, error, warn};
use uuid::Uuid;
use chrono::{DateTime, Utc, Duration};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{rand_core::OsRng, SaltString};

use crate::config::Config;
use crate::errors::SecurityError;

#[derive(Debug, Serialize, Deserialize)]
pub struct EncryptionRequest {
    pub data: String,
    pub key_id: Option<String>,
    pub context: Option<HashMap<String, String>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct EncryptionResponse {
    pub encrypted_data: String,
    pub key_id: String,
    pub nonce: String,
    pub context_hash: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DecryptionRequest {
    pub encrypted_data: String,
    pub key_id: String,
    pub nonce: String,
    pub context_hash: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HashRequest {
    pub data: String,
    pub salt: Option<String>,
    pub algorithm: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HashResponse {
    pub hash: String,
    pub salt: String,
    pub algorithm: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SignatureRequest {
    pub data: String,
    pub key_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SignatureResponse {
    pub signature: String,
    pub key_id: String,
    pub timestamp: DateTime<Utc>,
}

pub struct CryptoService {
    master_key: LessSafeKey,
    hmac_key: hmac::Key,
    rng: SystemRandom,
    key_rotation_interval: Duration,
    keys: HashMap<String, (LessSafeKey, DateTime<Utc>)>,
}

impl CryptoService {
    pub async fn new(config: &Config) -> Result<Self, SecurityError> {
        let rng = SystemRandom::new();
        
        // Initialize master key (in production, load from secure key management)
        let master_key_bytes = config.crypto.master_key.as_bytes();
        let unbound_key = UnboundKey::new(&AES_256_GCM, master_key_bytes)
            .map_err(|_| SecurityError::CryptoInitError("Invalid master key".to_string()))?;
        let master_key = LessSafeKey::new(unbound_key);
        
        // Initialize HMAC key
        let hmac_key = hmac::Key::new(hmac::HMAC_SHA256, master_key_bytes);
        
        let mut service = Self {
            master_key,
            hmac_key,
            rng,
            key_rotation_interval: Duration::hours(24),
            keys: HashMap::new(),
        };
        
        // Generate initial encryption keys
        service.rotate_keys().await?;
        
        info!("Crypto service initialized successfully");
        Ok(service)
    }
    
    pub async fn is_ready(&self) -> bool {
        !self.keys.is_empty()
    }
    
    async fn rotate_keys(&mut self) -> Result<(), SecurityError> {
        let key_id = Uuid::new_v4().to_string();
        let mut key_bytes = [0u8; 32];
        self.rng.fill(&mut key_bytes)
            .map_err(|_| SecurityError::CryptoError("Failed to generate key".to_string()))?;
        
        let unbound_key = UnboundKey::new(&AES_256_GCM, &key_bytes)
            .map_err(|_| SecurityError::CryptoError("Failed to create key".to_string()))?;
        let key = LessSafeKey::new(unbound_key);
        
        self.keys.insert(key_id.clone(), (key, Utc::now()));
        
        // Clean up old keys (keep last 3 rotations)
        if self.keys.len() > 3 {
            let mut sorted_keys: Vec<_> = self.keys.iter().collect();
            sorted_keys.sort_by(|a, b| a.1.1.cmp(&b.1.1));
            
            for (old_key_id, _) in sorted_keys.iter().take(self.keys.len() - 3) {
                self.keys.remove(*old_key_id);
            }
        }
        
        info!("Key rotation completed. New key ID: {}", key_id);
        Ok(())
    }
    
    pub async fn encrypt_data(&self, request: EncryptionRequest) -> Result<EncryptionResponse, SecurityError> {
        let key_id = request.key_id.unwrap_or_else(|| {
            // Get the most recent key
            self.keys.iter()
                .max_by(|a, b| a.1.1.cmp(&b.1.1))
                .map(|(k, _)| k.clone())
                .unwrap_or_default()
        });
        
        let (key, _) = self.keys.get(&key_id)
            .ok_or_else(|| SecurityError::CryptoError("Key not found".to_string()))?;
        
        // Generate nonce
        let mut nonce_bytes = [0u8; 12];
        self.rng.fill(&mut nonce_bytes)
            .map_err(|_| SecurityError::CryptoError("Failed to generate nonce".to_string()))?;
        let nonce = Nonce::assume_unique_for_key(nonce_bytes);
        
        // Prepare additional authenticated data
        let mut aad_data = Vec::new();
        let context_hash = if let Some(context) = &request.context {
            let context_json = serde_json::to_string(context)
                .map_err(|_| SecurityError::CryptoError("Invalid context".to_string()))?;
            let hash = self.compute_hash(&context_json, None)?;
            aad_data.extend_from_slice(hash.as_bytes());
            Some(hash)
        } else {
            None
        };
        
        let aad = Aad::from(&aad_data);
        
        // Encrypt the data
        let mut data_bytes = request.data.into_bytes();
        key.seal_in_place_append_tag(nonce, aad, &mut data_bytes)
            .map_err(|_| SecurityError::CryptoError("Encryption failed".to_string()))?;
        
        let encrypted_data = base64::encode(&data_bytes);
        let nonce_str = base64::encode(&nonce_bytes);
        
        Ok(EncryptionResponse {
            encrypted_data,
            key_id,
            nonce: nonce_str,
            context_hash,
        })
    }
    
    pub async fn decrypt_data(&self, request: DecryptionRequest) -> Result<String, SecurityError> {
        let (key, _) = self.keys.get(&request.key_id)
            .ok_or_else(|| SecurityError::CryptoError("Key not found".to_string()))?;
        
        // Decode nonce and encrypted data
        let nonce_bytes = base64::decode(&request.nonce)
            .map_err(|_| SecurityError::CryptoError("Invalid nonce".to_string()))?;
        let nonce = Nonce::try_assume_unique_for_key(&nonce_bytes)
            .map_err(|_| SecurityError::CryptoError("Invalid nonce".to_string()))?;
        
        let mut encrypted_bytes = base64::decode(&request.encrypted_data)
            .map_err(|_| SecurityError::CryptoError("Invalid encrypted data".to_string()))?;
        
        // Prepare AAD
        let mut aad_data = Vec::new();
        if let Some(context_hash) = &request.context_hash {
            aad_data.extend_from_slice(context_hash.as_bytes());
        }
        let aad = Aad::from(&aad_data);
        
        // Decrypt the data
        let decrypted_bytes = key.open_in_place(nonce, aad, &mut encrypted_bytes)
            .map_err(|_| SecurityError::CryptoError("Decryption failed".to_string()))?;
        
        let decrypted_string = String::from_utf8(decrypted_bytes.to_vec())
            .map_err(|_| SecurityError::CryptoError("Invalid UTF-8 data".to_string()))?;
        
        Ok(decrypted_string)
    }
    
    pub fn compute_hash(&self, data: &str, salt: Option<&str>) -> Result<String, SecurityError> {
        match salt {
            Some(salt_str) => {
                // Use Argon2 for password hashing
                let salt = SaltString::from_b64(salt_str)
                    .map_err(|_| SecurityError::CryptoError("Invalid salt".to_string()))?;
                
                let argon2 = Argon2::default();
                let password_hash = argon2.hash_password(data.as_bytes(), &salt)
                    .map_err(|_| SecurityError::CryptoError("Hash computation failed".to_string()))?;
                
                Ok(password_hash.to_string())
            }
            None => {
                // Use SHA-256 for general hashing
                let mut context = Context::new(&SHA256);
                context.update(data.as_bytes());
                let digest = context.finish();
                Ok(hex::encode(digest.as_ref()))
            }
        }
    }
    
    pub fn verify_hash(&self, data: &str, hash: &str) -> Result<bool, SecurityError> {
        if hash.starts_with("$argon2") {
            // Argon2 hash verification
            let parsed_hash = PasswordHash::new(hash)
                .map_err(|_| SecurityError::CryptoError("Invalid hash format".to_string()))?;
            
            let argon2 = Argon2::default();
            Ok(argon2.verify_password(data.as_bytes(), &parsed_hash).is_ok())
        } else {
            // SHA-256 hash verification
            let computed_hash = self.compute_hash(data, None)?;
            Ok(computed_hash == hash)
        }
    }
    
    pub fn generate_signature(&self, data: &str, key_id: Option<&str>) -> Result<SignatureResponse, SecurityError> {
        let signature_ctx = hmac::Context::with_key(&self.hmac_key);
        signature_ctx.update(data.as_bytes());
        signature_ctx.update(Utc::now().to_rfc3339().as_bytes());
        
        let signature = signature_ctx.sign();
        let signature_hex = hex::encode(signature.as_ref());
        
        Ok(SignatureResponse {
            signature: signature_hex,
            key_id: key_id.unwrap_or("default").to_string(),
            timestamp: Utc::now(),
        })
    }
    
    pub fn verify_signature(&self, data: &str, signature: &str, timestamp: DateTime<Utc>) -> Result<bool, SecurityError> {
        // Check timestamp (signature should not be older than 1 hour)
        if Utc::now().signed_duration_since(timestamp) > Duration::hours(1) {
            return Ok(false);
        }
        
        let verification_key = hmac::Key::new(hmac::HMAC_SHA256, self.hmac_key.as_ref());
        let mut ctx = hmac::Context::with_key(&verification_key);
        ctx.update(data.as_bytes());
        ctx.update(timestamp.to_rfc3339().as_bytes());
        
        let expected_signature = ctx.sign();
        let expected_hex = hex::encode(expected_signature.as_ref());
        
        Ok(expected_hex == signature)
    }
    
    pub async fn secure_random(&self, size: usize) -> Result<Vec<u8>, SecurityError> {
        let mut buffer = vec![0u8; size];
        self.rng.fill(&mut buffer)
            .map_err(|_| SecurityError::CryptoError("Failed to generate random data".to_string()))?;
        Ok(buffer)
    }
}

// HTTP handlers

pub async fn encrypt_handler(
    request: web::Json<EncryptionRequest>,
    state: web::Data<crate::AppState>,
) -> Result<HttpResponse> {
    match state.crypto_service.encrypt_data(request.into_inner()).await {
        Ok(response) => Ok(HttpResponse::Ok().json(response)),
        Err(e) => {
            error!("Encryption failed: {:?}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Encryption failed"
            })))
        }
    }
}

pub async fn decrypt_handler(
    request: web::Json<DecryptionRequest>,
    state: web::Data<crate::AppState>,
) -> Result<HttpResponse> {
    match state.crypto_service.decrypt_data(request.into_inner()).await {
        Ok(decrypted_data) => Ok(HttpResponse::Ok().json(serde_json::json!({
            "data": decrypted_data
        }))),
        Err(e) => {
            error!("Decryption failed: {:?}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Decryption failed"
            })))
        }
    }
}

pub async fn hash_handler(
    request: web::Json<HashRequest>,
    state: web::Data<crate::AppState>,
) -> Result<HttpResponse> {
    let salt = match &request.salt {
        Some(s) => Some(s.as_str()),
        None => None,
    };
    
    match state.crypto_service.compute_hash(&request.data, salt) {
        Ok(hash) => Ok(HttpResponse::Ok().json(HashResponse {
            hash,
            salt: request.salt.clone().unwrap_or_else(|| "none".to_string()),
            algorithm: request.algorithm.clone().unwrap_or_else(|| "sha256".to_string()),
        })),
        Err(e) => {
            error!("Hashing failed: {:?}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Hashing failed"
            })))
        }
    }
}

pub async fn sign_handler(
    request: web::Json<SignatureRequest>,
    state: web::Data<crate::AppState>,
) -> Result<HttpResponse> {
    let key_id = request.key_id.as_deref();
    
    match state.crypto_service.generate_signature(&request.data, key_id) {
        Ok(response) => Ok(HttpResponse::Ok().json(response)),
        Err(e) => {
            error!("Signing failed: {:?}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Signing failed"
            })))
        }
    }
}

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/crypto")
            .route("/encrypt", web::post().to(encrypt_handler))
            .route("/decrypt", web::post().to(decrypt_handler))
            .route("/hash", web::post().to(hash_handler))
            .route("/sign", web::post().to(sign_handler))
    );
}