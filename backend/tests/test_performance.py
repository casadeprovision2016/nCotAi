"""
Performance and concurrency tests for COTAI backend.
Tests for response times, throughput, load handling, and resource utilization.
"""
import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.factories import UserFactory, TenderFactory, QuotationFactory


@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformanceBaselines:
    """Tests for establishing performance baselines for critical endpoints."""
    
    async def test_auth_login_response_time(self, async_client: AsyncClient, test_user):
        """Test login endpoint meets response time requirements (<200ms)."""
        start_time = time.time()
        
        response = await async_client.post("/auth/login", json={
            "email": test_user.email,
            "password": "test_password"
        })
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 200, f"Login response time {response_time:.2f}ms exceeds 200ms threshold"
    
    async def test_tender_list_response_time(self, async_client: AsyncClient, authenticated_headers):
        """Test tender list endpoint meets response time requirements (<500ms)."""
        # Create test data
        tenders = [TenderFactory() for _ in range(50)]
        
        start_time = time.time()
        
        response = await async_client.get("/api/tenders", headers=authenticated_headers)
        
        response_time = (time.time() - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 500, f"Tender list response time {response_time:.2f}ms exceeds 500ms threshold"
    
    async def test_tender_search_response_time(self, async_client: AsyncClient, authenticated_headers):
        """Test tender search endpoint meets response time requirements (<1000ms)."""
        # Create test data with searchable content
        for i in range(100):
            TenderFactory(title=f"Construção de ponte {i}", description=f"Projeto de infraestrutura {i}")
        
        start_time = time.time()
        
        response = await async_client.get(
            "/api/tenders/search?q=construção&category=infrastructure",
            headers=authenticated_headers
        )
        
        response_time = (time.time() - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 1000, f"Search response time {response_time:.2f}ms exceeds 1000ms threshold"
    
    async def test_dashboard_load_time(self, async_client: AsyncClient, authenticated_headers):
        """Test dashboard data loading meets response time requirements (<300ms)."""
        start_time = time.time()
        
        response = await async_client.get("/api/dashboard/summary", headers=authenticated_headers)
        
        response_time = (time.time() - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time < 300, f"Dashboard load time {response_time:.2f}ms exceeds 300ms threshold"


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
class TestConcurrencyHandling:
    """Tests for concurrent user handling and race conditions."""
    
    async def test_concurrent_login_requests(self, async_client: AsyncClient):
        """Test system handles multiple concurrent login requests."""
        users = [UserFactory() for _ in range(20)]
        
        async def login_user(user):
            response = await async_client.post("/auth/login", json={
                "email": user.email,
                "password": "test_password"
            })
            return response.status_code, response.json()
        
        # Execute concurrent logins
        tasks = [login_user(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        successful_logins = 0
        for result in results:
            if not isinstance(result, Exception):
                status_code, data = result
                if status_code == status.HTTP_200_OK:
                    successful_logins += 1
        
        assert successful_logins >= 18, f"Only {successful_logins}/20 concurrent logins succeeded"
    
    async def test_concurrent_tender_creation(self, async_client: AsyncClient, authenticated_headers):
        """Test concurrent tender creation doesn't cause race conditions."""
        
        async def create_tender(tender_data):
            response = await async_client.post(
                "/api/tenders",
                json=tender_data,
                headers=authenticated_headers
            )
            return response.status_code, response.json()
        
        # Prepare test data
        tender_data_list = []
        for i in range(15):
            tender_data_list.append({
                "title": f"Concurrent Tender {i}",
                "description": f"Test tender created concurrently {i}",
                "category": "infrastructure",
                "estimated_value": 100000.0 + i * 1000,
                "deadline": (datetime.now() + timedelta(days=30)).isoformat()
            })
        
        # Execute concurrent creations
        tasks = [create_tender(data) for data in tender_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_creations = 0
        created_ids = set()
        
        for result in results:
            if not isinstance(result, Exception):
                status_code, data = result
                if status_code == status.HTTP_201_CREATED:
                    successful_creations += 1
                    created_ids.add(data.get("id"))
        
        assert successful_creations >= 13, f"Only {successful_creations}/15 concurrent creations succeeded"
        assert len(created_ids) == successful_creations, "Duplicate IDs detected - race condition occurred"
    
    async def test_concurrent_quotation_updates(self, async_client: AsyncClient, authenticated_headers):
        """Test concurrent quotation updates maintain data consistency."""
        # Create a quotation
        quotation = QuotationFactory()
        
        async def update_quotation(update_data):
            response = await async_client.put(
                f"/api/quotations/{quotation.id}",
                json=update_data,
                headers=authenticated_headers
            )
            return response.status_code, response.json()
        
        # Prepare concurrent updates
        updates = [
            {"status": "ACTIVE", "priority": "HIGH"},
            {"estimated_total": 50000.0},
            {"notes": f"Updated at {datetime.now().isoformat()}"},
            {"deadline": (datetime.now() + timedelta(days=15)).isoformat()},
            {"supplier_count": 5}
        ]
        
        # Execute concurrent updates
        tasks = [update_quotation(update) for update in updates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify at least some updates succeeded
        successful_updates = sum(
            1 for result in results 
            if not isinstance(result, Exception) and result[0] == status.HTTP_200_OK
        )
        
        assert successful_updates >= 3, f"Only {successful_updates}/5 concurrent updates succeeded"


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
class TestLoadTesting:
    """Load testing for system capacity under stress."""
    
    async def test_api_throughput_under_load(self, async_client: AsyncClient, authenticated_headers):
        """Test API can handle sustained load without degradation."""
        request_count = 100
        max_concurrent = 10
        
        async def make_request():
            response = await async_client.get("/api/tenders", headers=authenticated_headers)
            return response.status_code, time.time()
        
        # Execute load test
        start_time = time.time()
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_request():
            async with semaphore:
                return await make_request()
        
        tasks = [limited_request() for _ in range(request_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = 0
        response_times = []
        
        for result in results:
            if not isinstance(result, Exception):
                status_code, response_time = result
                if status_code == status.HTTP_200_OK:
                    successful_requests += 1
                    response_times.append(response_time - start_time)
        
        # Calculate metrics
        throughput = successful_requests / total_time
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        assert successful_requests >= request_count * 0.95, f"Only {successful_requests}/{request_count} requests succeeded"
        assert throughput >= 10, f"Throughput {throughput:.2f} req/s below minimum of 10 req/s"
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.2f}s exceeds 2s threshold"
    
    async def test_database_connection_pool_under_load(self, async_client: AsyncClient, authenticated_headers):
        """Test database connection pool handles concurrent requests efficiently."""
        
        async def database_intensive_request():
            # Request that requires multiple database queries
            response = await async_client.get(
                "/api/dashboard/analytics?include_charts=true&include_stats=true",
                headers=authenticated_headers
            )
            return response.status_code
        
        # Execute concurrent database-intensive requests
        concurrent_requests = 25
        tasks = [database_intensive_request() for _ in range(concurrent_requests)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Verify performance
        successful_requests = sum(
            1 for result in results 
            if not isinstance(result, Exception) and result == status.HTTP_200_OK
        )
        
        assert successful_requests >= concurrent_requests * 0.9, "Database connection pool failed under load"
        assert execution_time < 10.0, f"Database operations took {execution_time:.2f}s, exceeding 10s threshold"


@pytest.mark.performance
@pytest.mark.asyncio
class TestCachePerformance:
    """Tests for caching performance and efficiency."""
    
    @patch('app.services.cache.redis_client')
    async def test_cache_hit_performance(self, mock_redis, async_client: AsyncClient, authenticated_headers):
        """Test cache hits provide significant performance improvement."""
        # Mock cache hit
        mock_redis.get.return_value = '{"cached": true, "data": "test"}'
        
        # First request (cache miss simulation)
        start_time = time.time()
        response1 = await async_client.get("/api/tenders/statistics", headers=authenticated_headers)
        cache_miss_time = (time.time() - start_time) * 1000
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = await async_client.get("/api/tenders/statistics", headers=authenticated_headers)
        cache_hit_time = (time.time() - start_time) * 1000
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        # Cache hit should be significantly faster
        performance_improvement = (cache_miss_time - cache_hit_time) / cache_miss_time
        assert performance_improvement > 0.3, f"Cache only improved performance by {performance_improvement:.1%}"
    
    async def test_cache_warming_performance(self, async_client: AsyncClient, authenticated_headers):
        """Test cache warming strategies improve overall performance."""
        # Trigger cache warming
        await async_client.post("/api/admin/cache/warm", headers=authenticated_headers)
        
        # Test multiple requests to cached endpoints
        cached_endpoints = [
            "/api/dashboard/summary",
            "/api/tenders/statistics",
            "/api/users/activity-summary"
        ]
        
        total_response_time = 0
        request_count = 0
        
        for endpoint in cached_endpoints:
            for _ in range(3):  # Multiple requests to same endpoint
                start_time = time.time()
                response = await async_client.get(endpoint, headers=authenticated_headers)
                response_time = (time.time() - start_time) * 1000
                
                assert response.status_code == status.HTTP_200_OK
                total_response_time += response_time
                request_count += 1
        
        avg_response_time = total_response_time / request_count
        assert avg_response_time < 100, f"Average cached response time {avg_response_time:.2f}ms exceeds 100ms"


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
class TestMemoryAndResourceUsage:
    """Tests for memory usage and resource management."""
    
    async def test_memory_usage_under_load(self, async_client: AsyncClient, authenticated_headers):
        """Test memory usage remains stable under sustained load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create load that could cause memory leaks
        for batch in range(5):
            tasks = []
            for _ in range(20):
                tasks.append(
                    async_client.post("/api/tenders", json={
                        "title": f"Memory Test Tender {uuid.uuid4()}",
                        "description": "x" * 1000,  # Large description
                        "category": "infrastructure",
                        "estimated_value": 100000.0,
                        "deadline": (datetime.now() + timedelta(days=30)).isoformat()
                    }, headers=authenticated_headers)
                )
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check memory after each batch
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory
            
            # Memory should not grow excessively
            assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB in batch {batch}"
    
    async def test_file_upload_memory_efficiency(self, async_client: AsyncClient, authenticated_headers):
        """Test file uploads don't cause excessive memory usage."""
        import io
        
        # Create a mock large file
        large_file_content = b"x" * (5 * 1024 * 1024)  # 5MB file
        file_like = io.BytesIO(large_file_content)
        
        # Monitor memory during upload
        import psutil
        import os
        process = psutil.Process(os.getpid())
        
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Simulate file upload
        with patch('app.services.file_storage.save_file') as mock_save:
            mock_save.return_value = "file_id_123"
            
            response = await async_client.post(
                "/api/tenders/upload-document",
                files={"file": ("test.pdf", file_like, "application/pdf")},
                headers=authenticated_headers
            )
        
        post_upload_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = post_upload_memory - initial_memory
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert memory_increase < 50, f"File upload increased memory by {memory_increase:.2f}MB"


@pytest.mark.performance
@pytest.mark.asyncio
class TestScalabilityMetrics:
    """Tests for measuring system scalability characteristics."""
    
    async def test_user_session_scalability(self, async_client: AsyncClient):
        """Test system can handle multiple concurrent user sessions."""
        session_count = 50
        
        # Create multiple user sessions
        sessions = []
        for i in range(session_count):
            user = UserFactory()
            login_response = await async_client.post("/auth/login", json={
                "email": user.email,
                "password": "test_password"
            })
            
            if login_response.status_code == status.HTTP_200_OK:
                token = login_response.json()["access_token"]
                sessions.append({"Authorization": f"Bearer {token}"})
        
        # Test concurrent operations from all sessions
        async def session_operation(session_headers):
            response = await async_client.get("/api/dashboard/summary", headers=session_headers)
            return response.status_code == status.HTTP_200_OK
        
        tasks = [session_operation(session) for session in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_operations = sum(1 for result in results if result is True)
        success_rate = successful_operations / len(sessions)
        
        assert success_rate >= 0.9, f"Only {success_rate:.1%} of concurrent sessions succeeded"
    
    async def test_pagination_performance_at_scale(self, async_client: AsyncClient, authenticated_headers):
        """Test pagination performance with large datasets."""
        # Create large dataset
        batch_size = 100
        total_records = 1000
        
        for batch in range(total_records // batch_size):
            tenders = [
                TenderFactory(title=f"Scale Test Tender {batch}_{i}")
                for i in range(batch_size)
            ]
        
        # Test pagination at different offsets
        page_sizes = [10, 25, 50, 100]
        offsets = [0, 100, 500, 900]
        
        for page_size in page_sizes:
            for offset in offsets:
                start_time = time.time()
                
                response = await async_client.get(
                    f"/api/tenders?limit={page_size}&offset={offset}",
                    headers=authenticated_headers
                )
                
                response_time = (time.time() - start_time) * 1000
                
                assert response.status_code == status.HTTP_200_OK
                assert response_time < 1000, f"Pagination (limit={page_size}, offset={offset}) took {response_time:.2f}ms"
                
                data = response.json()
                assert len(data.get("items", [])) <= page_size


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
class TestPerformanceRegression:
    """Tests to detect performance regressions."""
    
    async def test_critical_path_performance_baseline(self, async_client: AsyncClient, authenticated_headers):
        """Test critical user journeys meet performance baselines."""
        
        # Critical Path 1: User login to dashboard view
        start_time = time.time()
        
        # Login already done via fixture, test dashboard access
        dashboard_response = await async_client.get("/api/dashboard/summary", headers=authenticated_headers)
        
        login_to_dashboard_time = (time.time() - start_time) * 1000
        
        assert dashboard_response.status_code == status.HTTP_200_OK
        assert login_to_dashboard_time < 500, f"Login to dashboard took {login_to_dashboard_time:.2f}ms"
        
        # Critical Path 2: Tender search and view
        start_time = time.time()
        
        search_response = await async_client.get(
            "/api/tenders/search?q=infraestrutura",
            headers=authenticated_headers
        )
        
        search_time = (time.time() - start_time) * 1000
        
        assert search_response.status_code == status.HTTP_200_OK
        assert search_time < 800, f"Tender search took {search_time:.2f}ms"
        
        # Critical Path 3: Quotation creation
        start_time = time.time()
        
        quotation_data = {
            "title": "Performance Test Quotation",
            "tender_id": str(uuid.uuid4()),
            "estimated_total": 50000.0,
            "deadline": (datetime.now() + timedelta(days=15)).isoformat()
        }
        
        create_response = await async_client.post(
            "/api/quotations",
            json=quotation_data,
            headers=authenticated_headers
        )
        
        creation_time = (time.time() - start_time) * 1000
        
        assert create_response.status_code == status.HTTP_201_CREATED
        assert creation_time < 300, f"Quotation creation took {creation_time:.2f}ms"
    
    async def test_database_query_performance(self, async_client: AsyncClient, authenticated_headers):
        """Test database queries maintain acceptable performance."""
        
        # Test complex analytical query
        start_time = time.time()
        
        analytics_response = await async_client.get(
            "/api/analytics/tender-performance?period=6months&include_details=true",
            headers=authenticated_headers
        )
        
        query_time = (time.time() - start_time) * 1000
        
        assert analytics_response.status_code == status.HTTP_200_OK
        assert query_time < 2000, f"Complex analytics query took {query_time:.2f}ms"
        
        # Test aggregation query
        start_time = time.time()
        
        stats_response = await async_client.get(
            "/api/statistics/summary?group_by=category,status",
            headers=authenticated_headers
        )
        
        aggregation_time = (time.time() - start_time) * 1000
        
        assert stats_response.status_code == status.HTTP_200_OK
        assert aggregation_time < 1000, f"Aggregation query took {aggregation_time:.2f}ms"