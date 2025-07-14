"""
Factory classes for creating test data using factory_boy.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

import factory
from factory import Faker, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.user import User, UserRole, RefreshToken, AuditLog, LoginAttempt
from app.models.tender import (
    Tender,
    TenderStatus,
    TenderCategory,
    TenderType,
    GovernmentEntity,
    TenderItem,
    TenderDocument,
    Proposal,
    ProposalStatus,
)
from app.models.quotation import (
    Quotation,
    QuotationStatus,
    QuotationPriority,
    QuotationItem,
    Supplier,
    QuotationDocument,
)
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationStatus,
    NotificationTemplate,
)


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configurations."""
    
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    id = factory.LazyFunction(uuid.uuid4)
    email = Faker("email")
    hashed_password = factory.LazyFunction(
        lambda: "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "secret"
    )
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    company_name = Faker("company")
    role = factory.Iterator(UserRole)
    permissions = factory.LazyFunction(lambda: {"read": True, "write": False})
    is_active = True
    is_verified = True
    is_superuser = False
    mfa_enabled = False
    mfa_secret = None
    backup_codes = None
    last_login = None
    failed_login_attempts = 0
    locked_until = None
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AdminUserFactory(UserFactory):
    """Factory for creating Admin User instances."""
    
    role = UserRole.ADMIN
    permissions = factory.LazyFunction(lambda: {"read": True, "write": True, "admin": True})
    is_superuser = True


class SuperUserFactory(UserFactory):
    """Factory for creating Super User instances."""
    
    role = UserRole.SUPER_ADMIN
    permissions = factory.LazyFunction(lambda: {"read": True, "write": True, "admin": True, "super_admin": True})
    is_superuser = True


class UserWithMFAFactory(UserFactory):
    """Factory for creating User instances with MFA enabled."""
    
    mfa_enabled = True
    mfa_secret = "JBSWY3DPEHPK3PXP"
    backup_codes = factory.LazyFunction(lambda: ["123456", "789012", "345678"])


class RefreshTokenFactory(BaseFactory):
    """Factory for creating RefreshToken instances."""
    
    class Meta:
        model = RefreshToken
    
    id = factory.LazyFunction(uuid.uuid4)
    user = SubFactory(UserFactory)
    token = factory.LazyFunction(lambda: str(uuid.uuid4()))
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=7))
    is_revoked = False
    device_info = factory.LazyFunction(lambda: {"browser": "Chrome", "os": "Windows"})
    created_at = factory.LazyFunction(datetime.utcnow)


class AuditLogFactory(BaseFactory):
    """Factory for creating AuditLog instances."""
    
    class Meta:
        model = AuditLog
    
    id = factory.LazyFunction(uuid.uuid4)
    user = SubFactory(UserFactory)
    action = Faker("word")
    resource = Faker("word")
    resource_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    old_values = factory.LazyFunction(lambda: {"status": "old"})
    new_values = factory.LazyFunction(lambda: {"status": "new"})
    ip_address = Faker("ipv4")
    user_agent = Faker("user_agent")
    timestamp = factory.LazyFunction(datetime.utcnow)


class LoginAttemptFactory(BaseFactory):
    """Factory for creating LoginAttempt instances."""
    
    class Meta:
        model = LoginAttempt
    
    id = factory.LazyFunction(uuid.uuid4)
    email = Faker("email")
    ip_address = Faker("ipv4")
    success = True
    failure_reason = None
    user_agent = Faker("user_agent")
    timestamp = factory.LazyFunction(datetime.utcnow)


class FailedLoginAttemptFactory(LoginAttemptFactory):
    """Factory for creating failed LoginAttempt instances."""
    
    success = False
    failure_reason = "Invalid credentials"


class GovernmentEntityFactory(BaseFactory):
    """Factory for creating GovernmentEntity instances."""
    
    class Meta:
        model = GovernmentEntity
    
    id = factory.LazyFunction(uuid.uuid4)
    name = Faker("company")
    cnpj = factory.LazyFunction(lambda: "12.345.678/0001-90")
    type = factory.Iterator(["FEDERAL", "STATE", "MUNICIPAL"])
    level = factory.Iterator(["FEDERAL", "STATE", "MUNICIPAL"])
    contact_email = Faker("email")
    contact_phone = Faker("phone_number")
    address = Faker("address")
    city = Faker("city")
    state = Faker("state_abbr")
    zipcode = Faker("zipcode")
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class TenderFactory(BaseFactory):
    """Factory for creating Tender instances."""
    
    class Meta:
        model = Tender
    
    id = factory.LazyFunction(uuid.uuid4)
    title = Faker("sentence", nb_words=8)
    description = Faker("text", max_nb_chars=500)
    government_entity = SubFactory(GovernmentEntityFactory)
    category = factory.Iterator(TenderCategory)
    type = factory.Iterator(TenderType)
    status = factory.Iterator(TenderStatus)
    estimated_value = Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    publication_date = factory.LazyFunction(lambda: datetime.utcnow().date())
    deadline = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(days=30)).date())
    opening_date = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(days=35)).date())
    external_id = factory.LazyFunction(lambda: f"EXT-{uuid.uuid4().hex[:8]}")
    external_url = Faker("url")
    requirements = factory.LazyFunction(lambda: {"qualification": "Basic", "experience": "2 years"})
    evaluation_criteria = factory.LazyFunction(lambda: {"price": 70, "technical": 30})
    ai_score = Faker("pyfloat", left_digits=1, right_digits=2, positive=True, max_value=10)
    ai_analysis = factory.LazyFunction(lambda: {"risk_level": "LOW", "relevance": "HIGH"})
    created_by = SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class TenderItemFactory(BaseFactory):
    """Factory for creating TenderItem instances."""
    
    class Meta:
        model = TenderItem
    
    id = factory.LazyFunction(uuid.uuid4)
    tender = SubFactory(TenderFactory)
    item_number = factory.Sequence(lambda n: n + 1)
    description = Faker("sentence", nb_words=10)
    quantity = Faker("pyint", min_value=1, max_value=100)
    unit = Faker("word")
    estimated_unit_price = Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    estimated_total_price = factory.LazyAttribute(
        lambda obj: obj.quantity * obj.estimated_unit_price
    )
    specifications = factory.LazyFunction(lambda: {"material": "Steel", "size": "Medium"})
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class TenderDocumentFactory(BaseFactory):
    """Factory for creating TenderDocument instances."""
    
    class Meta:
        model = TenderDocument
    
    id = factory.LazyFunction(uuid.uuid4)
    tender = SubFactory(TenderFactory)
    name = Faker("file_name", extension="pdf")
    file_path = factory.LazyAttribute(lambda obj: f"/documents/{obj.name}")
    file_size = Faker("pyint", min_value=1000, max_value=10000000)
    mime_type = "application/pdf"
    document_type = factory.Iterator(["EDICT", "ANNEXES", "SPECIFICATIONS", "PROPOSAL_FORM"])
    is_required = True
    ocr_text = Faker("text", max_nb_chars=1000)
    ai_analysis = factory.LazyFunction(lambda: {"clauses": 5, "risks": 2})
    uploaded_by = SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class ProposalFactory(BaseFactory):
    """Factory for creating Proposal instances."""
    
    class Meta:
        model = Proposal
    
    id = factory.LazyFunction(uuid.uuid4)
    tender = SubFactory(TenderFactory)
    submitted_by = SubFactory(UserFactory)
    status = factory.Iterator(ProposalStatus)
    total_value = Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    proposal_data = factory.LazyFunction(lambda: {"technical_score": 85, "commercial_score": 90})
    submission_date = factory.LazyFunction(datetime.utcnow)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class SupplierFactory(BaseFactory):
    """Factory for creating Supplier instances."""
    
    class Meta:
        model = Supplier
    
    id = factory.LazyFunction(uuid.uuid4)
    name = Faker("company")
    cnpj = factory.LazyFunction(lambda: "98.765.432/0001-10")
    contact_email = Faker("email")
    contact_phone = Faker("phone_number")
    address = Faker("address")
    city = Faker("city")
    state = Faker("state_abbr")
    zipcode = Faker("zipcode")
    specialties = factory.LazyFunction(lambda: ["Construction", "Engineering"])
    rating = Faker("pyfloat", left_digits=1, right_digits=1, positive=True, max_value=5)
    is_active = True
    created_by = SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class QuotationFactory(BaseFactory):
    """Factory for creating Quotation instances."""
    
    class Meta:
        model = Quotation
    
    id = factory.LazyFunction(uuid.uuid4)
    title = Faker("sentence", nb_words=6)
    description = Faker("text", max_nb_chars=300)
    tender = SubFactory(TenderFactory)
    status = factory.Iterator(QuotationStatus)
    priority = factory.Iterator(QuotationPriority)
    estimated_value = Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    deadline = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(days=15)).date())
    requirements = factory.LazyFunction(lambda: {"delivery": "30 days", "warranty": "1 year"})
    created_by = SubFactory(UserFactory)
    assigned_to = SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class QuotationItemFactory(BaseFactory):
    """Factory for creating QuotationItem instances."""
    
    class Meta:
        model = QuotationItem
    
    id = factory.LazyFunction(uuid.uuid4)
    quotation = SubFactory(QuotationFactory)
    item_number = factory.Sequence(lambda n: n + 1)
    description = Faker("sentence", nb_words=8)
    quantity = Faker("pyint", min_value=1, max_value=50)
    unit = Faker("word")
    unit_price = Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    total_price = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)
    supplier = SubFactory(SupplierFactory)
    notes = Faker("text", max_nb_chars=200)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class QuotationDocumentFactory(BaseFactory):
    """Factory for creating QuotationDocument instances."""
    
    class Meta:
        model = QuotationDocument
    
    id = factory.LazyFunction(uuid.uuid4)
    quotation = SubFactory(QuotationFactory)
    name = Faker("file_name", extension="pdf")
    file_path = factory.LazyAttribute(lambda obj: f"/documents/{obj.name}")
    file_size = Faker("pyint", min_value=1000, max_value=5000000)
    mime_type = "application/pdf"
    document_type = factory.Iterator(["QUOTATION", "TECHNICAL_SPEC", "COMMERCIAL_PROPOSAL"])
    uploaded_by = SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class NotificationTemplateFactory(BaseFactory):
    """Factory for creating NotificationTemplate instances."""
    
    class Meta:
        model = NotificationTemplate
    
    id = factory.LazyFunction(uuid.uuid4)
    name = Faker("word")
    category = factory.Iterator(NotificationCategory)
    subject = Faker("sentence", nb_words=5)
    content = Faker("text", max_nb_chars=200)
    variables = factory.LazyFunction(lambda: ["user_name", "tender_title"])
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class NotificationFactory(BaseFactory):
    """Factory for creating Notification instances."""
    
    class Meta:
        model = Notification
    
    id = factory.LazyFunction(uuid.uuid4)
    user = SubFactory(UserFactory)
    category = factory.Iterator(NotificationCategory)
    title = Faker("sentence", nb_words=4)
    message = Faker("text", max_nb_chars=300)
    status = factory.Iterator(NotificationStatus)
    priority = factory.Iterator(["LOW", "MEDIUM", "HIGH", "URGENT"])
    data = factory.LazyFunction(lambda: {"tender_id": str(uuid.uuid4())})
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=30))
    read_at = None
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


# Convenience factory functions
def create_test_user(**kwargs) -> User:
    """Create a test user with default values."""
    return UserFactory(**kwargs)


def create_admin_user(**kwargs) -> User:
    """Create an admin user with default values."""
    return AdminUserFactory(**kwargs)


def create_test_tender(**kwargs) -> Tender:
    """Create a test tender with default values."""
    return TenderFactory(**kwargs)


def create_test_quotation(**kwargs) -> Quotation:
    """Create a test quotation with default values."""
    return QuotationFactory(**kwargs)


def create_test_notification(**kwargs) -> Notification:
    """Create a test notification with default values."""
    return NotificationFactory(**kwargs)


def create_bulk_users(count: int, **kwargs) -> list[User]:
    """Create multiple test users."""
    return [UserFactory(**kwargs) for _ in range(count)]


def create_bulk_tenders(count: int, **kwargs) -> list[Tender]:
    """Create multiple test tenders."""
    return [TenderFactory(**kwargs) for _ in range(count)]


def create_bulk_quotations(count: int, **kwargs) -> list[Quotation]:
    """Create multiple test quotations."""
    return [QuotationFactory(**kwargs) for _ in range(count)]


# Factory traits for common scenarios
class TenderWithItemsFactory(TenderFactory):
    """Factory for creating Tender with items."""
    
    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            for item_data in extracted:
                TenderItemFactory(tender=obj, **item_data)
        else:
            # Create 3 default items
            for i in range(3):
                TenderItemFactory(tender=obj)


class TenderWithDocumentsFactory(TenderFactory):
    """Factory for creating Tender with documents."""
    
    @factory.post_generation
    def documents(obj, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            for doc_data in extracted:
                TenderDocumentFactory(tender=obj, **doc_data)
        else:
            # Create 2 default documents
            for i in range(2):
                TenderDocumentFactory(tender=obj)


class QuotationWithItemsFactory(QuotationFactory):
    """Factory for creating Quotation with items."""
    
    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            for item_data in extracted:
                QuotationItemFactory(quotation=obj, **item_data)
        else:
            # Create 2 default items
            for i in range(2):
                QuotationItemFactory(quotation=obj)


class CompleteTenderFactory(TenderFactory):
    """Factory for creating complete Tender with items and documents."""
    
    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        if not create:
            return
        for i in range(3):
            TenderItemFactory(tender=obj)
    
    @factory.post_generation
    def documents(obj, create, extracted, **kwargs):
        if not create:
            return
        for i in range(2):
            TenderDocumentFactory(tender=obj)


class CompleteQuotationFactory(QuotationFactory):
    """Factory for creating complete Quotation with items and documents."""
    
    @factory.post_generation
    def items(obj, create, extracted, **kwargs):
        if not create:
            return
        for i in range(2):
            QuotationItemFactory(quotation=obj)
    
    @factory.post_generation
    def documents(obj, create, extracted, **kwargs):
        if not create:
            return
        for i in range(1):
            QuotationDocumentFactory(quotation=obj)