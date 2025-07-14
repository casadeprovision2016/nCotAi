"""
AI Models Manager
Handles loading and management of various AI/ML models for tender analysis
"""

import asyncio
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import torch
import numpy as np
from transformers import (
    AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
    pipeline, Pipeline
)
import spacy
from spacy import Language
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from app.core.config import get_settings
from app.models.analysis import (
    AnalysisResult, EntityExtraction, RiskAssessment, 
    RelevanceScore, ComplianceCheck
)

logger = logging.getLogger(__name__)


class AIModelManager:
    """Manages all AI/ML models for tender analysis"""
    
    def __init__(self):
        self.settings = get_settings()
        self.models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.pipelines: Dict[str, Pipeline] = {}
        self.nlp: Optional[Language] = None
        self.models_loaded = False
        
    async def load_models(self):
        """Load all required AI models"""
        try:
            logger.info("Starting to load AI models...")
            
            # Load Portuguese language model
            await self._load_spacy_model()
            
            # Load BERT-based models for Portuguese
            await self._load_bert_models()
            
            # Load classification models
            await self._load_classification_models()
            
            # Load custom trained models
            await self._load_custom_models()
            
            # Create analysis pipelines
            await self._setup_pipelines()
            
            self.models_loaded = True
            logger.info("All AI models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load AI models: {e}")
            raise
    
    async def _load_spacy_model(self):
        """Load spaCy Portuguese model"""
        try:
            # Download model if not present
            try:
                self.nlp = spacy.load("pt_core_news_sm")
            except OSError:
                logger.warning("Portuguese model not found, using fallback")
                # In production, ensure the model is pre-installed
                self.nlp = spacy.blank("pt")
                
            logger.info("spaCy Portuguese model loaded")
            
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
    
    async def _load_bert_models(self):
        """Load BERT-based models for text analysis"""
        try:
            # Portuguese BERT model
            model_name = "neuralmind/bert-base-portuguese-cased"
            
            self.tokenizers["bert_pt"] = AutoTokenizer.from_pretrained(model_name)
            self.models["bert_pt"] = AutoModel.from_pretrained(model_name)
            
            # Classification model for risk assessment
            self.models["risk_classifier"] = AutoModelForSequenceClassification.from_pretrained(
                model_name, num_labels=3  # low, medium, high risk
            )
            
            logger.info("BERT models loaded")
            
        except Exception as e:
            logger.error(f"Failed to load BERT models: {e}")
            # Use fallback models
            self._load_fallback_models()
    
    def _load_fallback_models(self):
        """Load simpler fallback models if BERT fails"""
        logger.info("Loading fallback models...")
        # Initialize simple models as fallback
        self.models["tfidf"] = TfidfVectorizer(max_features=5000, stop_words=None)
        self.models["risk_classifier_simple"] = RandomForestClassifier(n_estimators=100)
    
    async def _load_classification_models(self):
        """Load classification models for various tasks"""
        try:
            # Tender relevance classifier
            self.models["relevance_classifier"] = LogisticRegression()
            
            # Document type classifier
            self.models["doc_type_classifier"] = RandomForestClassifier(n_estimators=50)
            
            # Compliance checker
            self.models["compliance_classifier"] = LogisticRegression()
            
            logger.info("Classification models initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize classification models: {e}")
            raise
    
    async def _load_custom_models(self):
        """Load custom trained models if available"""
        try:
            models_dir = Path(self.settings.models_path)
            
            # Load pre-trained custom models if they exist
            custom_models = [
                "tender_scoring_model.pkl",
                "risk_assessment_model.pkl",
                "entity_extraction_model.pkl"
            ]
            
            for model_file in custom_models:
                model_path = models_dir / model_file
                if model_path.exists():
                    model_name = model_file.replace(".pkl", "")
                    self.models[model_name] = joblib.load(model_path)
                    logger.info(f"Loaded custom model: {model_name}")
            
        except Exception as e:
            logger.warning(f"No custom models loaded: {e}")
    
    async def _setup_pipelines(self):
        """Setup analysis pipelines"""
        try:
            # Text classification pipeline
            if "bert_pt" in self.models:
                self.pipelines["sentiment"] = pipeline(
                    "sentiment-analysis",
                    model=self.models["bert_pt"],
                    tokenizer=self.tokenizers["bert_pt"]
                )
            
            # Named Entity Recognition pipeline
            if self.nlp:
                self.pipelines["ner"] = self.nlp
            
            logger.info("Analysis pipelines setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup pipelines: {e}")
            raise
    
    async def extract_entities(self, text: str) -> EntityExtraction:
        """Extract named entities from text"""
        try:
            entities = []
            
            if self.nlp:
                doc = self.nlp(text)
                
                for ent in doc.ents:
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "confidence": 0.85  # Default confidence
                    })
            
            # Extract specific patterns for tender documents
            tender_entities = self._extract_tender_specific_entities(text)
            entities.extend(tender_entities)
            
            return EntityExtraction(
                entities=entities,
                processing_time=0.1,  # Placeholder
                confidence=0.85
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return EntityExtraction(entities=[], processing_time=0, confidence=0)
    
    def _extract_tender_specific_entities(self, text: str) -> List[Dict]:
        """Extract tender-specific entities using regex patterns"""
        import re
        
        entities = []
        patterns = {
            "CNPJ": r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',
            "CPF": r'\d{3}\.\d{3}\.\d{3}-\d{2}',
            "CURRENCY": r'R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?',
            "DATE": r'\d{1,2}/\d{1,2}/\d{4}',
            "PROCESS_NUMBER": r'\d{4,6}/\d{4}',
            "CEP": r'\d{5}-\d{3}'
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append({
                    "text": match.group(),
                    "label": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9
                })
        
        return entities
    
    async def assess_risk(self, text: str, context: Dict = None) -> RiskAssessment:
        """Assess risk level of tender document"""
        try:
            # High-risk keywords and patterns
            high_risk_keywords = [
                "inexequível", "impugnação", "rescisão unilateral",
                "multa superior", "garantia acima", "prazo inexequível"
            ]
            
            medium_risk_keywords = [
                "multa", "penalidade", "garantia", "caução",
                "exclusividade", "vistoria obrigatória"
            ]
            
            low_risk_indicators = [
                "pregão eletrônico", "menor preço", "técnica e preço",
                "cadastro nacional", "habilitação simplificada"
            ]
            
            text_lower = text.lower()
            
            # Calculate risk score
            high_risk_count = sum(1 for keyword in high_risk_keywords 
                                if keyword in text_lower)
            medium_risk_count = sum(1 for keyword in medium_risk_keywords 
                                  if keyword in text_lower)
            low_risk_count = sum(1 for keyword in low_risk_indicators 
                               if keyword in text_lower)
            
            # Weighted scoring
            risk_score = (high_risk_count * 0.7 + medium_risk_count * 0.4 - 
                         low_risk_count * 0.2)
            
            # Normalize to 0-1 range
            risk_score = max(0, min(1, risk_score / 5))
            
            # Determine risk level
            if risk_score > 0.7:
                risk_level = "HIGH"
            elif risk_score > 0.4:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # Identify specific risks
            identified_risks = []
            for keyword in high_risk_keywords:
                if keyword in text_lower:
                    identified_risks.append({
                        "type": "contractual",
                        "description": f"High-risk clause detected: {keyword}",
                        "severity": "high",
                        "recommendation": "Careful legal review required"
                    })
            
            return RiskAssessment(
                risk_level=risk_level,
                risk_score=risk_score,
                identified_risks=identified_risks,
                recommendations=self._generate_risk_recommendations(risk_level),
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return RiskAssessment(
                risk_level="UNKNOWN",
                risk_score=0.5,
                identified_risks=[],
                recommendations=[],
                confidence=0
            )
    
    def _generate_risk_recommendations(self, risk_level: str) -> List[str]:
        """Generate recommendations based on risk level"""
        recommendations = {
            "HIGH": [
                "Conduct thorough legal review",
                "Consult with specialized legal team",
                "Consider risk mitigation strategies",
                "Evaluate if participation is viable"
            ],
            "MEDIUM": [
                "Review contract terms carefully",
                "Prepare contingency plans",
                "Calculate risk premiums in pricing"
            ],
            "LOW": [
                "Standard due diligence recommended",
                "Review standard contract terms"
            ]
        }
        
        return recommendations.get(risk_level, ["Standard review recommended"])
    
    async def calculate_relevance_score(self, text: str, company_profile: Dict) -> RelevanceScore:
        """Calculate relevance score for a tender"""
        try:
            base_score = 0.5
            
            # Company expertise matching
            company_keywords = company_profile.get("keywords", [])
            expertise_score = self._calculate_expertise_match(text, company_keywords)
            
            # Tender type scoring
            tender_type_score = self._score_tender_type(text)
            
            # Geographic preference
            location_score = self._score_location(text, company_profile.get("location"))
            
            # Value range compatibility
            value_score = self._score_value_range(text, company_profile.get("value_range"))
            
            # Weighted final score
            final_score = (
                base_score * 0.2 +
                expertise_score * 0.4 +
                tender_type_score * 0.2 +
                location_score * 0.1 +
                value_score * 0.1
            )
            
            return RelevanceScore(
                score=min(1.0, final_score),
                factors={
                    "expertise_match": expertise_score,
                    "tender_type": tender_type_score,
                    "location": location_score,
                    "value_range": value_score
                },
                confidence=0.85
            )
            
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return RelevanceScore(score=0.5, factors={}, confidence=0)
    
    def _calculate_expertise_match(self, text: str, company_keywords: List[str]) -> float:
        """Calculate expertise match score"""
        if not company_keywords:
            return 0.5
        
        text_lower = text.lower()
        matches = sum(1 for keyword in company_keywords 
                     if keyword.lower() in text_lower)
        
        return min(1.0, matches / len(company_keywords))
    
    def _score_tender_type(self, text: str) -> float:
        """Score based on tender type preferences"""
        text_lower = text.lower()
        
        preferred_types = {
            "pregão eletrônico": 0.9,
            "concorrência": 0.7,
            "convite": 0.8,
            "menor preço": 0.8,
            "técnica e preço": 0.6
        }
        
        for tender_type, score in preferred_types.items():
            if tender_type in text_lower:
                return score
        
        return 0.5
    
    def _score_location(self, text: str, preferred_location: str) -> float:
        """Score based on geographic preferences"""
        if not preferred_location:
            return 0.5
        
        text_lower = text.lower()
        location_lower = preferred_location.lower()
        
        if location_lower in text_lower:
            return 1.0
        
        # Check for state match
        states = {
            "são paulo": ["sp", "são paulo"],
            "rio de janeiro": ["rj", "rio de janeiro"],
            "minas gerais": ["mg", "minas gerais"]
        }
        
        for state, variants in states.items():
            if any(variant in text_lower for variant in variants):
                if state == location_lower or location_lower in variants:
                    return 0.8
        
        return 0.3
    
    def _score_value_range(self, text: str, value_range: Dict) -> float:
        """Score based on value range compatibility"""
        if not value_range:
            return 0.5
        
        # Extract monetary values from text
        import re
        currency_pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
        matches = re.findall(currency_pattern, text)
        
        if not matches:
            return 0.5
        
        # Convert to float (simplified)
        try:
            max_value = value_range.get("max", float('inf'))
            min_value = value_range.get("min", 0)
            
            # Use the largest value found in text
            tender_value = 0
            for match in matches:
                value_str = match.replace('.', '').replace(',', '.')
                value = float(value_str)
                tender_value = max(tender_value, value)
            
            if min_value <= tender_value <= max_value:
                return 1.0
            elif tender_value < min_value:
                return 0.3
            else:
                return 0.6  # Above range but might be worth it
                
        except (ValueError, TypeError):
            return 0.5
    
    async def check_compliance(self, text: str, requirements: List[str]) -> ComplianceCheck:
        """Check compliance with specific requirements"""
        try:
            compliance_results = []
            overall_compliance = True
            
            for requirement in requirements:
                is_compliant = self._check_single_requirement(text, requirement)
                compliance_results.append({
                    "requirement": requirement,
                    "compliant": is_compliant,
                    "confidence": 0.8
                })
                
                if not is_compliant:
                    overall_compliance = False
            
            return ComplianceCheck(
                overall_compliant=overall_compliance,
                requirements_check=compliance_results,
                missing_requirements=[
                    r["requirement"] for r in compliance_results 
                    if not r["compliant"]
                ],
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return ComplianceCheck(
                overall_compliant=False,
                requirements_check=[],
                missing_requirements=[],
                confidence=0
            )
    
    def _check_single_requirement(self, text: str, requirement: str) -> bool:
        """Check if a single requirement is mentioned in the text"""
        text_lower = text.lower()
        requirement_lower = requirement.lower()
        
        # Simple keyword matching (in production, use more sophisticated NLP)
        return requirement_lower in text_lower