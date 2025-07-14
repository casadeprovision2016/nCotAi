"""
Intelligent Scoring Engine
Advanced ML-based scoring system for tender relevance and opportunity assessment
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass

from app.models.analysis import ScoringResult, CompanyProfile, TenderDocument
from app.services.ai_models import AIModelManager
from app.services.cache import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class ScoringFeatures:
    """Features used for scoring calculation"""
    keyword_match_score: float
    historical_success_rate: float
    company_capability_score: float
    competition_level: float
    value_alignment_score: float
    geographic_preference: float
    timeline_feasibility: float
    risk_adjusted_score: float
    market_opportunity_score: float


class ScoringEngine:
    """Intelligent scoring engine for tender opportunities"""
    
    def __init__(self, ai_manager: AIModelManager, cache_manager: CacheManager):
        self.ai_manager = ai_manager
        self.cache_manager = cache_manager
        self.feature_weights = self._initialize_feature_weights()
        self.scoring_models = {}
        
    def _initialize_feature_weights(self) -> Dict[str, float]:
        """Initialize feature weights for scoring algorithm"""
        return {
            "keyword_match": 0.25,
            "historical_success": 0.20,
            "company_capability": 0.15,
            "competition_level": 0.10,
            "value_alignment": 0.10,
            "geographic_preference": 0.08,
            "timeline_feasibility": 0.07,
            "risk_adjustment": 0.05
        }
    
    async def calculate_tender_score(
        self, 
        tender: TenderDocument, 
        company_profile: CompanyProfile,
        historical_data: Optional[Dict] = None
    ) -> ScoringResult:
        """Calculate comprehensive tender opportunity score"""
        try:
            # Check cache first
            cache_key = f"score:{tender.id}:{company_profile.id}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                return ScoringResult.parse_obj(cached_result)
            
            # Extract features
            features = await self._extract_scoring_features(
                tender, company_profile, historical_data
            )
            
            # Calculate base score
            base_score = await self._calculate_base_score(features)
            
            # Apply ML model if available
            ml_score = await self._apply_ml_scoring(tender, company_profile, features)
            
            # Combine scores
            final_score = self._combine_scores(base_score, ml_score)
            
            # Generate detailed explanation
            explanation = self._generate_score_explanation(features, final_score)
            
            # Calculate confidence
            confidence = self._calculate_confidence(features, tender)
            
            result = ScoringResult(
                tender_id=tender.id,
                company_id=company_profile.id,
                overall_score=final_score,
                confidence=confidence,
                features=features,
                explanation=explanation,
                recommendations=self._generate_recommendations(features, final_score),
                calculated_at=datetime.utcnow()
            )
            
            # Cache result
            await self.cache_manager.set(
                cache_key, 
                result.dict(), 
                expire=timedelta(hours=6)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Scoring calculation failed for tender {tender.id}: {e}")
            return self._create_fallback_score(tender.id, company_profile.id)
    
    async def _extract_scoring_features(
        self,
        tender: TenderDocument,
        company_profile: CompanyProfile,
        historical_data: Optional[Dict]
    ) -> ScoringFeatures:
        """Extract features for scoring calculation"""
        
        # Keyword matching
        keyword_score = await self._calculate_keyword_match(
            tender.content, company_profile.keywords
        )
        
        # Historical success rate
        historical_score = self._calculate_historical_success(
            company_profile, tender.category, historical_data
        )
        
        # Company capability assessment
        capability_score = self._assess_company_capability(
            company_profile, tender
        )
        
        # Competition level estimation
        competition_score = await self._estimate_competition_level(tender)
        
        # Value alignment
        value_score = self._calculate_value_alignment(
            tender.estimated_value, company_profile.typical_contract_value
        )
        
        # Geographic preference
        geo_score = self._calculate_geographic_score(
            tender.location, company_profile.preferred_locations
        )
        
        # Timeline feasibility
        timeline_score = self._assess_timeline_feasibility(
            tender.deadline, company_profile.capacity
        )
        
        # Risk adjustment
        risk_assessment = await self.ai_manager.assess_risk(tender.content)
        risk_score = 1.0 - risk_assessment.risk_score
        
        # Market opportunity
        market_score = await self._calculate_market_opportunity(tender)
        
        return ScoringFeatures(
            keyword_match_score=keyword_score,
            historical_success_rate=historical_score,
            company_capability_score=capability_score,
            competition_level=competition_score,
            value_alignment_score=value_score,
            geographic_preference=geo_score,
            timeline_feasibility=timeline_score,
            risk_adjusted_score=risk_score,
            market_opportunity_score=market_score
        )
    
    async def _calculate_keyword_match(
        self, 
        tender_content: str, 
        company_keywords: List[str]
    ) -> float:
        """Calculate keyword matching score using advanced NLP"""
        if not company_keywords:
            return 0.5
        
        # Use AI model for semantic similarity
        try:
            # Simple keyword matching for now
            content_lower = tender_content.lower()
            matches = 0
            total_weight = 0
            
            for keyword in company_keywords:
                weight = 1.0  # All keywords have equal weight for now
                total_weight += weight
                
                if keyword.lower() in content_lower:
                    matches += weight
                    
                # Check for related terms (simplified)
                related_terms = self._get_related_terms(keyword)
                for term in related_terms:
                    if term.lower() in content_lower:
                        matches += weight * 0.5  # Partial credit for related terms
                        break
            
            if total_weight == 0:
                return 0.5
                
            score = min(1.0, matches / total_weight)
            return score
            
        except Exception as e:
            logger.error(f"Keyword matching failed: {e}")
            return 0.5
    
    def _get_related_terms(self, keyword: str) -> List[str]:
        """Get related terms for a keyword (simplified)"""
        relations = {
            "software": ["sistema", "aplicativo", "tecnologia", "TI"],
            "construção": ["obra", "edificação", "engenharia", "infraestrutura"],
            "consultoria": ["assessoria", "serviços", "análise", "planejamento"],
            "manutenção": ["reparo", "conservação", "assistência técnica"],
            "limpeza": ["higienização", "asseio", "conservação"],
        }
        
        return relations.get(keyword.lower(), [])
    
    def _calculate_historical_success(
        self,
        company_profile: CompanyProfile,
        tender_category: str,
        historical_data: Optional[Dict]
    ) -> float:
        """Calculate historical success rate for similar tenders"""
        if not historical_data:
            return 0.5  # Default score when no historical data
        
        # Look for similar categories
        category_data = historical_data.get("categories", {})
        similar_category_data = category_data.get(tender_category, {})
        
        if similar_category_data:
            won = similar_category_data.get("won", 0)
            total = similar_category_data.get("total", 1)
            success_rate = won / total
            
            # Apply recency weighting (more recent data is more relevant)
            recency_factor = similar_category_data.get("recency_factor", 1.0)
            
            return min(1.0, success_rate * recency_factor)
        
        # Fallback to overall success rate
        overall_success = historical_data.get("overall_success_rate", 0.15)
        return min(1.0, overall_success * 1.2)  # Slight boost for diversification
    
    def _assess_company_capability(
        self,
        company_profile: CompanyProfile,
        tender: TenderDocument
    ) -> float:
        """Assess company capability to fulfill tender requirements"""
        score = 0.0
        factors = 0
        
        # Team size vs project size
        if tender.estimated_value and company_profile.annual_revenue:
            value_ratio = tender.estimated_value / company_profile.annual_revenue
            if value_ratio < 0.1:  # Small project relative to company
                score += 0.9
            elif value_ratio < 0.3:  # Medium project
                score += 0.7
            elif value_ratio < 0.5:  # Large project
                score += 0.5
            else:  # Very large project
                score += 0.2
            factors += 1
        
        # Experience level
        experience_years = company_profile.years_of_experience or 0
        if experience_years >= 10:
            score += 0.9
        elif experience_years >= 5:
            score += 0.7
        elif experience_years >= 2:
            score += 0.5
        else:
            score += 0.3
        factors += 1
        
        # Certification and compliance
        if company_profile.certifications:
            cert_score = min(1.0, len(company_profile.certifications) * 0.2)
            score += cert_score
            factors += 1
        
        # Current capacity
        if company_profile.capacity:
            capacity_utilization = company_profile.capacity.get("utilization", 0.7)
            if capacity_utilization < 0.8:  # Has capacity
                score += 0.8
            elif capacity_utilization < 0.9:  # Limited capacity
                score += 0.6
            else:  # At capacity
                score += 0.3
            factors += 1
        
        return score / max(factors, 1)
    
    async def _estimate_competition_level(self, tender: TenderDocument) -> float:
        """Estimate competition level for the tender"""
        competition_score = 0.5  # Default medium competition
        
        # Factors that increase competition
        high_competition_indicators = [
            "pregão eletrônico",
            "menor preço",
            "ampla concorrência",
            "nacional"
        ]
        
        # Factors that decrease competition  
        low_competition_indicators = [
            "convite",
            "técnica e preço",
            "local",
            "especializada",
            "certificação específica"
        ]
        
        content_lower = tender.content.lower()
        
        for indicator in high_competition_indicators:
            if indicator in content_lower:
                competition_score += 0.1
        
        for indicator in low_competition_indicators:
            if indicator in content_lower:
                competition_score -= 0.1
        
        # Value-based competition estimation
        if tender.estimated_value:
            if tender.estimated_value < 100000:  # Low value = high competition
                competition_score += 0.1
            elif tender.estimated_value > 1000000:  # High value = medium competition
                competition_score -= 0.05
        
        return max(0.1, min(0.9, competition_score))
    
    def _calculate_value_alignment(
        self,
        tender_value: Optional[float],
        company_typical_value: Optional[float]
    ) -> float:
        """Calculate how well tender value aligns with company's typical contracts"""
        if not tender_value or not company_typical_value:
            return 0.5
        
        ratio = tender_value / company_typical_value
        
        # Optimal range is 0.5x to 2x typical value
        if 0.5 <= ratio <= 2.0:
            return 1.0
        elif 0.2 <= ratio < 0.5 or 2.0 < ratio <= 4.0:
            return 0.7
        elif 0.1 <= ratio < 0.2 or 4.0 < ratio <= 8.0:
            return 0.4
        else:
            return 0.1
    
    def _calculate_geographic_score(
        self,
        tender_location: str,
        preferred_locations: List[str]
    ) -> float:
        """Calculate geographic preference score"""
        if not preferred_locations:
            return 0.5
        
        tender_location_lower = tender_location.lower()
        
        for preferred in preferred_locations:
            if preferred.lower() in tender_location_lower:
                return 1.0
        
        # Check for same state
        state_mapping = {
            "sp": ["são paulo", "santos", "campinas", "guarulhos"],
            "rj": ["rio de janeiro", "niterói", "nova iguaçu"],
            "mg": ["belo horizonte", "contagem", "uberlândia"]
        }
        
        for state, cities in state_mapping.items():
            if any(city in tender_location_lower for city in cities):
                for preferred in preferred_locations:
                    if state in preferred.lower() or any(city in preferred.lower() for city in cities):
                        return 0.7
        
        return 0.3  # Different region
    
    def _assess_timeline_feasibility(
        self,
        tender_deadline: datetime,
        company_capacity: Optional[Dict]
    ) -> float:
        """Assess if timeline is feasible given company capacity"""
        if not company_capacity:
            return 0.7  # Default assumption
        
        days_until_deadline = (tender_deadline - datetime.utcnow()).days
        
        # Very tight deadline
        if days_until_deadline < 7:
            return 0.2
        elif days_until_deadline < 15:
            return 0.5
        elif days_until_deadline < 30:
            return 0.8
        else:
            return 1.0
    
    async def _calculate_market_opportunity(self, tender: TenderDocument) -> float:
        """Calculate market opportunity score"""
        opportunity_score = 0.5
        
        # Check for growth sectors
        growth_keywords = [
            "digital", "tecnologia", "sustentabilidade", "energia renovável",
            "inovação", "modernização", "automação"
        ]
        
        content_lower = tender.content.lower()
        for keyword in growth_keywords:
            if keyword in content_lower:
                opportunity_score += 0.1
        
        # Multi-year contracts increase opportunity
        if "plurianual" in content_lower or "múltiplos anos" in content_lower:
            opportunity_score += 0.2
        
        return min(1.0, opportunity_score)
    
    async def _calculate_base_score(self, features: ScoringFeatures) -> float:
        """Calculate base score using weighted features"""
        weighted_score = (
            features.keyword_match_score * self.feature_weights["keyword_match"] +
            features.historical_success_rate * self.feature_weights["historical_success"] +
            features.company_capability_score * self.feature_weights["company_capability"] +
            (1 - features.competition_level) * self.feature_weights["competition_level"] +
            features.value_alignment_score * self.feature_weights["value_alignment"] +
            features.geographic_preference * self.feature_weights["geographic_preference"] +
            features.timeline_feasibility * self.feature_weights["timeline_feasibility"] +
            features.risk_adjusted_score * self.feature_weights["risk_adjustment"]
        )
        
        return min(1.0, weighted_score)
    
    async def _apply_ml_scoring(
        self,
        tender: TenderDocument,
        company_profile: CompanyProfile,
        features: ScoringFeatures
    ) -> Optional[float]:
        """Apply ML model for scoring if available"""
        try:
            # Check if custom ML model is available
            if "tender_scoring_model" in self.ai_manager.models:
                model = self.ai_manager.models["tender_scoring_model"]
                
                # Prepare feature vector
                feature_vector = np.array([
                    features.keyword_match_score,
                    features.historical_success_rate,
                    features.company_capability_score,
                    features.competition_level,
                    features.value_alignment_score,
                    features.geographic_preference,
                    features.timeline_feasibility,
                    features.risk_adjusted_score,
                    features.market_opportunity_score
                ]).reshape(1, -1)
                
                # Predict score
                ml_score = model.predict(feature_vector)[0]
                return max(0.0, min(1.0, ml_score))
            
            return None
            
        except Exception as e:
            logger.error(f"ML scoring failed: {e}")
            return None
    
    def _combine_scores(self, base_score: float, ml_score: Optional[float]) -> float:
        """Combine base score with ML score"""
        if ml_score is None:
            return base_score
        
        # Weighted combination (70% ML, 30% base)
        combined = 0.7 * ml_score + 0.3 * base_score
        return min(1.0, combined)
    
    def _generate_score_explanation(
        self, 
        features: ScoringFeatures, 
        final_score: float
    ) -> Dict[str, Any]:
        """Generate detailed explanation of the score"""
        return {
            "overall_score": final_score,
            "score_category": self._get_score_category(final_score),
            "key_strengths": self._identify_strengths(features),
            "key_weaknesses": self._identify_weaknesses(features),
            "feature_breakdown": {
                "keyword_match": {
                    "score": features.keyword_match_score,
                    "weight": self.feature_weights["keyword_match"],
                    "contribution": features.keyword_match_score * self.feature_weights["keyword_match"]
                },
                "historical_success": {
                    "score": features.historical_success_rate,
                    "weight": self.feature_weights["historical_success"],
                    "contribution": features.historical_success_rate * self.feature_weights["historical_success"]
                },
                "company_capability": {
                    "score": features.company_capability_score,
                    "weight": self.feature_weights["company_capability"],
                    "contribution": features.company_capability_score * self.feature_weights["company_capability"]
                }
            }
        }
    
    def _get_score_category(self, score: float) -> str:
        """Categorize score into descriptive labels"""
        if score >= 0.8:
            return "Excelente Oportunidade"
        elif score >= 0.65:
            return "Boa Oportunidade"
        elif score >= 0.5:
            return "Oportunidade Moderada"
        elif score >= 0.35:
            return "Oportunidade Limitada"
        else:
            return "Baixa Prioridade"
    
    def _identify_strengths(self, features: ScoringFeatures) -> List[str]:
        """Identify key strengths based on features"""
        strengths = []
        
        if features.keyword_match_score > 0.7:
            strengths.append("Alta compatibilidade com expertise da empresa")
        
        if features.historical_success_rate > 0.6:
            strengths.append("Histórico positivo em categoria similar")
        
        if features.company_capability_score > 0.7:
            strengths.append("Empresa bem posicionada para executar")
        
        if features.competition_level < 0.4:
            strengths.append("Baixa concorrência esperada")
        
        if features.value_alignment_score > 0.8:
            strengths.append("Valor alinhado com perfil da empresa")
        
        if features.geographic_preference > 0.8:
            strengths.append("Localização preferencial")
        
        return strengths
    
    def _identify_weaknesses(self, features: ScoringFeatures) -> List[str]:
        """Identify key weaknesses based on features"""
        weaknesses = []
        
        if features.keyword_match_score < 0.3:
            weaknesses.append("Baixa compatibilidade com expertise")
        
        if features.competition_level > 0.7:
            weaknesses.append("Alta concorrência esperada")
        
        if features.timeline_feasibility < 0.4:
            weaknesses.append("Prazo muito apertado")
        
        if features.risk_adjusted_score < 0.5:
            weaknesses.append("Riscos contratuais identificados")
        
        if features.value_alignment_score < 0.3:
            weaknesses.append("Valor fora do perfil típico")
        
        return weaknesses
    
    def _generate_recommendations(
        self, 
        features: ScoringFeatures, 
        final_score: float
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if final_score > 0.7:
            recommendations.append("Priorizar esta oportunidade")
            recommendations.append("Preparar proposta competitiva")
        
        if features.competition_level > 0.6:
            recommendations.append("Desenvolver estratégia diferenciada")
            recommendations.append("Considerar parcerias estratégicas")
        
        if features.timeline_feasibility < 0.5:
            recommendations.append("Avaliar viabilidade do cronograma")
            recommendations.append("Considerar recursos adicionais")
        
        if features.risk_adjusted_score < 0.6:
            recommendations.append("Revisar riscos contratuais")
            recommendations.append("Consultar equipe jurídica")
        
        if final_score < 0.4:
            recommendations.append("Considerar não participar")
            recommendations.append("Focar em oportunidades mais alinhadas")
        
        return recommendations
    
    def _calculate_confidence(
        self, 
        features: ScoringFeatures, 
        tender: TenderDocument
    ) -> float:
        """Calculate confidence level of the scoring"""
        confidence_factors = []
        
        # Data completeness
        if tender.content and len(tender.content) > 1000:
            confidence_factors.append(0.9)
        elif tender.content and len(tender.content) > 500:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Feature reliability
        reliable_features = 0
        total_features = 0
        
        for feature_name, feature_value in features.__dict__.items():
            total_features += 1
            if 0.1 <= feature_value <= 0.9:  # Not extreme values
                reliable_features += 1
        
        if total_features > 0:
            feature_reliability = reliable_features / total_features
            confidence_factors.append(feature_reliability)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _create_fallback_score(self, tender_id: str, company_id: str) -> ScoringResult:
        """Create fallback score when calculation fails"""
        return ScoringResult(
            tender_id=tender_id,
            company_id=company_id,
            overall_score=0.5,
            confidence=0.3,
            features=ScoringFeatures(
                keyword_match_score=0.5,
                historical_success_rate=0.5,
                company_capability_score=0.5,
                competition_level=0.5,
                value_alignment_score=0.5,
                geographic_preference=0.5,
                timeline_feasibility=0.5,
                risk_adjusted_score=0.5,
                market_opportunity_score=0.5
            ),
            explanation={"error": "Scoring calculation failed, using fallback"},
            recommendations=["Review tender manually"],
            calculated_at=datetime.utcnow()
        )