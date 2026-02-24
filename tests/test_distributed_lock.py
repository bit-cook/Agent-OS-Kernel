# -*- coding: utf-8 -*-
"""
Distributed Lock Tests
"""

import asyncio
import pytest
import time
from agent_os_kernel.core.distributed_lock import (
    DistributedLock,
    ReadWriteLock,
    InMemoryLockBackend,
    ReadWriteLockBackend,
    LockType,
    LockTimeoutError,
    create_distributed_lock,
    create_read_write_lock,
)


class TestDistributedLock:
    """Test cases for DistributedLock"""
    
    @pytest.fixture
    def lock(self):
        """Create a distributed lock instance"""
        return create_distributed_lock(InMemoryLockBackend())
    
    @pytest.fixture
    def rw_lock(self):
        """Create a read-write lock instance"""
        return create_read_write_lock(ReadWriteLockBackend())
    
    @pytest.mark.asyncio
    async def test_mutex_lock_basic(self, lock):
        """Test basic mutex lock acquisition and release"""
        lock_name = "test_mutex_1"
        owner_id = await lock.acquire_mutex(lock_name)
        
        # Verify lock is acquired
        assert await lock.is_locked(lock_name) is True
        
        # Release the lock
        released = await lock.release(lock_name, owner_id)
        assert released is True
        
        # Verify lock is released
        assert await lock.is_locked(lock_name) is False
    
    @pytest.mark.asyncio
    async def test_mutex_lock_exclusive(self, lock):
        """Test that mutex lock is exclusive"""
        lock_name = "test_mutex_2"
        
        # First acquisition should succeed
        owner1 = await lock.acquire_mutex(lock_name, timeout=1.0)
        assert owner1 is not None
        
        # Second acquisition should fail (no timeout)
        try:
            owner2 = await lock.acquire_mutex(lock_name, timeout=0.1)
            assert False, "Should have raised LockTimeoutError"
        except LockTimeoutError:
            pass
        
        # Release the first lock
        await lock.release(lock_name, owner1)
        
        # Now we should be able to acquire again
        owner2 = await lock.acquire_mutex(lock_name, timeout=1.0)
        assert owner2 is not None
        assert owner2 != owner1
        
        await lock.release(lock_name, owner2)
    
    @pytest.mark.asyncio
    async def test_mutex_lock_with_context_manager(self, lock):
        """Test mutex lock with context manager"""
        lock_name = "test_mutex_3"
        
        async with lock.mutex_lock(lock_name) as owner_id:
            assert await lock.is_locked(lock_name) is True
            # Simulate work
            await asyncio.sleep(0.01)
        
        # After context exit, lock should be released
        assert await lock.is_locked(lock_name) is False
    
    @pytest.mark.asyncio
    async def test_rw_lock_read_multiple(self, rw_lock):
        """Test that multiple read locks can be acquired simultaneously"""
        lock_name = "test_rw_read"
        
        # Acquire multiple read locks
        owner1 = await rw_lock.acquire_read(lock_name)
        owner2 = await rw_lock.acquire_read(lock_name)
        
        # Both should succeed
        assert owner1 is not None
        assert owner2 is not None
        assert owner1 != owner2
        
        # Release both
        await rw_lock.release_read(lock_name, owner1)
        await rw_lock.release_read(lock_name, owner2)
        
        assert await rw_lock.backend.is_locked(lock_name) is False
    
    @pytest.mark.asyncio
    async def test_rw_lock_write_exclusive(self, rw_lock):
        """Test that write lock is exclusive"""
        lock_name = "test_rw_write"
        
        # Acquire write lock
        owner1 = await rw_lock.acquire_write(lock_name)
        assert owner1 is not None
        
        # Try to acquire read lock (should fail)
        try:
            owner2 = await rw_lock.acquire_read(lock_name, timeout=0.1)
            assert False, "Should have raised LockTimeoutError"
        except LockTimeoutError:
            pass
        
        # Try to acquire another write lock (should fail)
        try:
            owner3 = await rw_lock.acquire_write(lock_name, timeout=0.1)
            assert False, "Should have raised LockTimeoutError"
        except LockTimeoutError:
            pass
        
        # Release write lock
        await rw_lock.release_write(lock_name, owner1)
        
        # Now we can acquire read lock
        owner2 = await rw_lock.acquire_read(lock_name)
        assert owner2 is not None
        await rw_lock.release_read(lock_name, owner2)
    
    @pytest.mark.asyncio
    async def test_rw_lock_write_blocks_read(self, rw_lock):
        """Test that write lock blocks read locks"""
        lock_name = "test_rw_block"
        
        # Acquire write lock
        write_owner = await rw_lock.acquire_write(lock_name)
        
        # Read acquisition should timeout
        with pytest.raises(LockTimeoutError):
            await rw_lock.acquire_read(lock_name, timeout=0.1)
        
        # Release write lock
        await rw_lock.release_write(lock_name, write_owner)
        
        # Now read should succeed
        read_owner = await rw_lock.acquire_read(lock_name)
        assert read_owner is not None
        await rw_lock.release_read(lock_name, read_owner)
    
    @pytest.mark.asyncio
    async def test_timeout_mechanism(self, lock):
        """Test lock timeout mechanism"""
        lock_name = "test_timeout_1"
        
        # Acquire lock with very short timeout for testing
        owner = await lock.acquire_mutex(lock_name, timeout=1.0, expire=0.1)
        
        # Wait for lock to expire
        await asyncio.sleep(0.15)
        
        # Backend should report lock as not locked (expired)
        lock.backend.cleanup_expired()
        assert await lock.is_locked(lock_name) is False
    
    @pytest.mark.asyncio
    async def test_lock_renewal(self, lock):
        """Test lock renewal mechanism"""
        lock_name = "test_renewal_1"
        expire_time = 0.3
        
        # Acquire lock
        owner = await lock.acquire_mutex(lock_name, expire=expire_time)
        original_info = await lock.get_lock_info(lock_name)
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Renew the lock
        success = await lock.renew(lock_name, owner, expire=expire_time)
        assert success is True
        
        # Check that renewals count increased
        renewed_info = await lock.get_lock_info(lock_name)
        assert renewed_info["renewals"] == original_info["renewals"] + 1
        assert renewed_info["expire_time"] > original_info["expire_time"]
        
        await lock.release(lock_name, owner)
    
    @pytest.mark.asyncio
    async def test_periodic_renewal(self, lock):
        """Test periodic lock renewal"""
        lock_name = "test_periodic_renewal"
        expire_time = 0.3
        renewal_interval = 0.1
        
        # Acquire lock
        owner = await lock.acquire_mutex(lock_name, expire=expire_time)
        
        renewal_count = 0
        def renewal_callback(success, lock_name, owner_id):
            nonlocal renewal_count
            if success:
                renewal_count += 1
        
        # Start periodic renewal
        task = await lock.renew_periodically(
            lock_name, owner, expire=expire_time, 
            interval=renewal_interval, callback=renewal_callback
        )
        
        # Wait for multiple renewals
        await asyncio.sleep(0.35)
        
        # Cancel renewal task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Check that renewals occurred
        assert renewal_count >= 2
        
        # Lock should still be valid
        info = await lock.get_lock_info(lock_name)
        assert info["renewals"] >= 2
        
        await lock.release(lock_name, owner)
    
    @pytest.mark.asyncio
    async def test_lock_info(self, lock):
        """Test lock information retrieval"""
        lock_name = "test_info_1"
        
        # Acquire lock
        owner = await lock.acquire_mutex(lock_name, expire=30.0)
        
        # Get lock info
        info = await lock.get_lock_info(lock_name)
        
        assert info is not None
        assert info["lock_name"] == lock_name
        assert info["owner_id"] == owner
        assert info["lock_type"] == "mutex"
        assert info["renewals"] == 0
        assert info["is_expired"] is False
        
        await lock.release(lock_name, owner)
    
    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisition(self, lock):
        """Test concurrent lock acquisition"""
        lock_name = "test_concurrent"
        acquired_count = 0
        lock_holders = []
        
        async def try_acquire():
            nonlocal acquired_count
            try:
                owner = await lock.acquire_mutex(lock_name, timeout=0.5)
                async with lock.mutex_lock(lock_name, owner_id=owner):
                    # Critical section
                    await asyncio.sleep(0.05)
                acquired_count += 1
                lock_holders.append(owner)
            except LockTimeoutError:
                pass
        
        # Launch multiple concurrent acquisition attempts
        tasks = [try_acquire() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Only one should have acquired the lock
        assert acquired_count == 1
    
    @pytest.mark.asyncio
    async def test_wrong_owner_release(self, lock):
        """Test that wrong owner cannot release lock"""
        lock_name = "test_wrong_owner"
        
        # Acquire lock
        owner = await lock.acquire_mutex(lock_name)
        
        # Try to release with wrong owner
        success = await lock.release(lock_name, "wrong_owner_id")
        assert success is False
        
        # Lock should still be held
        assert await lock.is_locked(lock_name) is True
        
        # Release with correct owner
        success = await lock.release(lock_name, owner)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_rw_lock_context_managers(self, rw_lock):
        """Test read-write lock context managers"""
        lock_name = "test_context"
        
        # Use read context
        async with rw_lock.read(lock_name) as read_owner:
            assert await rw_lock.backend.is_locked(lock_name) is True
        
        # Lock should be released
        assert await rw_lock.backend.is_locked(lock_name) is False
        
        # Use write context
        async with rw_lock.write(lock_name) as write_owner:
            assert await rw_lock.backend.is_locked(lock_name) is True
        
        # Lock should be released
        assert await rw_lock.backend.is_locked(lock_name) is False
    
    @pytest.mark.asyncio
    async def test_read_write_lock_info(self, rw_lock):
        """Test read-write lock information"""
        lock_name = "test_rw_info"
        
        # Acquire read lock
        owner = await rw_lock.acquire_read(lock_name, expire=30.0)
        
        # Get info from backend
        backend_owner = await rw_lock.backend.get_owner(lock_name)
        
        assert backend_owner is not None
        assert backend_owner.owner_id == owner
        assert backend_owner.lock_type == LockType.READ
        
        await rw_lock.release_read(lock_name, owner)
    
    @pytest.mark.asyncio
    async def test_inmemory_backend_cleanup(self):
        """Test in-memory backend expired lock cleanup"""
        backend = InMemoryLockBackend()
        lock = DistributedLock(backend)
        
        lock_name = "test_cleanup"
        
        # Acquire lock with very short expire time
        owner = await lock.acquire_mutex(lock_name, expire=0.1)
        
        # Wait for expiration
        await asyncio.sleep(0.15)
        
        # Lock should still be in backend but marked as expired
        owner_info = await backend.get_owner(lock_name)
        assert owner_info is not None
        assert owner_info.is_expired(time.time()) is True
        
        # Cleanup expired locks
        backend.cleanup_expired()
        
        # Lock should be removed
        owner_info = await backend.get_owner(lock_name)
        assert owner_info is None


class TestDistributedLockFactory:
    """Test distributed lock factory functions"""
    
    def test_create_distributed_lock(self):
        """Test create_distributed_lock factory"""
        lock = create_distributed_lock()
        assert isinstance(lock, DistributedLock)
        assert isinstance(lock.backend, InMemoryLockBackend)
    
    def test_create_distributed_lock_with_backend(self):
        """Test create_distributed_lock with custom backend"""
        backend = InMemoryLockBackend()
        lock = create_distributed_lock(backend)
        assert lock.backend is backend
    
    def test_create_read_write_lock(self):
        """Test create_read_write_lock factory"""
        rw_lock = create_read_write_lock()
        assert isinstance(rw_lock, ReadWriteLock)
        assert isinstance(rw_lock.backend, ReadWriteLockBackend)
    
    def test_create_read_write_lock_with_backend(self):
        """Test create_read_write_lock with custom backend"""
        backend = ReadWriteLockBackend()
        rw_lock = create_read_write_lock(backend)
        assert rw_lock.backend is backend
