"""Tests for API Authentication"""
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rpi'))

from api.auth.api_key import APIKeyAuth, generate_api_key, APIKeyInfo


class TestAPIKeyGeneration(unittest.TestCase):
    """Test API key generation"""
    
    def test_generate_key_format(self):
        """Test generated key format"""
        key = generate_api_key()
        self.assertTrue(key.startswith("mia_api_"))
        self.assertEqual(len(key), len("mia_api_") + 32)  # 32 hex chars
    
    def test_generate_key_custom_prefix(self):
        """Test custom prefix"""
        key = generate_api_key(prefix="test")
        self.assertTrue(key.startswith("test_api_"))
    
    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique"""
        keys = [generate_api_key() for _ in range(100)]
        self.assertEqual(len(keys), len(set(keys)))


class TestAPIKeyAuth(unittest.TestCase):
    """Test API key authentication"""
    
    def setUp(self):
        """Create fresh auth instance for each test"""
        # Clear environment variables
        os.environ.pop('MIA_API_KEY', None)
        os.environ.pop('MIA_API_KEYS', None)
        os.environ.pop('MIA_AUTH_DISABLED', None)
        
        self.auth = APIKeyAuth()
    
    def test_add_and_verify_key(self):
        """Test adding and verifying a key"""
        key = generate_api_key()
        self.auth.add_key(key, "Test Key")
        
        info = self.auth.verify(key)
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "Test Key")
    
    def test_invalid_key_returns_none(self):
        """Test that invalid key returns None"""
        info = self.auth.verify("invalid_key_12345")
        self.assertIsNone(info)
    
    def test_key_scopes(self):
        """Test key scope checking"""
        key = generate_api_key()
        self.auth.add_key(key, "Limited Key", scopes=["read"])
        
        self.assertTrue(self.auth.has_scope(key, "read"))
        self.assertFalse(self.auth.has_scope(key, "write"))
        self.assertFalse(self.auth.has_scope(key, "admin"))
    
    def test_admin_scope_has_all_access(self):
        """Test that admin scope grants all access"""
        key = generate_api_key()
        self.auth.add_key(key, "Admin Key", scopes=["admin"])
        
        self.assertTrue(self.auth.has_scope(key, "read"))
        self.assertTrue(self.auth.has_scope(key, "write"))
        self.assertTrue(self.auth.has_scope(key, "admin"))
    
    def test_disable_key(self):
        """Test disabling a key"""
        key = generate_api_key()
        self.auth.add_key(key, "Test Key")
        
        # Key should work initially
        self.assertIsNotNone(self.auth.verify(key))
        
        # Disable key
        self.auth.disable_key(key)
        
        # Key should no longer work
        self.assertIsNone(self.auth.verify(key))
    
    def test_remove_key(self):
        """Test removing a key"""
        key = generate_api_key()
        self.auth.add_key(key, "Test Key")
        
        result = self.auth.remove_key(key)
        self.assertTrue(result)
        
        # Key should no longer work
        self.assertIsNone(self.auth.verify(key))
    
    def test_list_keys(self):
        """Test listing keys"""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        self.auth.add_key(key1, "Key 1")
        self.auth.add_key(key2, "Key 2")
        
        keys = self.auth.list_keys()
        self.assertEqual(len(keys), 2)
        names = [k.name for k in keys]
        self.assertIn("Key 1", names)
        self.assertIn("Key 2", names)
    
    def test_last_used_updated(self):
        """Test that last_used is updated on verify"""
        key = generate_api_key()
        self.auth.add_key(key, "Test Key")
        
        info1 = self.auth.verify(key)
        last_used1 = info1.last_used
        
        import time
        time.sleep(0.1)
        
        info2 = self.auth.verify(key)
        last_used2 = info2.last_used
        
        self.assertGreater(last_used2, last_used1)


class TestAPIKeyAuthEnvironment(unittest.TestCase):
    """Test API key auth with environment variables"""
    
    def tearDown(self):
        """Clean up environment variables"""
        os.environ.pop('MIA_API_KEY', None)
        os.environ.pop('MIA_API_KEYS', None)
        os.environ.pop('MIA_AUTH_DISABLED', None)
    
    def test_load_master_key_from_env(self):
        """Test loading master key from environment"""
        os.environ['MIA_API_KEY'] = 'test_master_key_12345'
        
        auth = APIKeyAuth()
        
        info = auth.verify('test_master_key_12345')
        self.assertIsNotNone(info)
        self.assertIn("admin", info.scopes)
    
    def test_load_multiple_keys_from_env(self):
        """Test loading multiple keys from environment"""
        os.environ['MIA_API_KEYS'] = 'key1,key2,key3'
        
        auth = APIKeyAuth()
        
        self.assertIsNotNone(auth.verify('key1'))
        self.assertIsNotNone(auth.verify('key2'))
        self.assertIsNotNone(auth.verify('key3'))
    
    def test_auth_disabled(self):
        """Test auth disabled mode"""
        os.environ['MIA_AUTH_DISABLED'] = '1'
        
        auth = APIKeyAuth()
        
        self.assertFalse(auth.enabled)
        
        # Any key should work when disabled
        info = auth.verify('any_random_key')
        self.assertIsNotNone(info)
        self.assertIn("admin", info.scopes)


class TestAPIKeyInfo(unittest.TestCase):
    """Test APIKeyInfo dataclass"""
    
    def test_default_scopes(self):
        """Test default scopes"""
        from datetime import datetime
        info = APIKeyInfo(
            key_id="test",
            name="Test",
            created_at=datetime.now()
        )
        self.assertIn("read", info.scopes)
        self.assertIn("write", info.scopes)
    
    def test_enabled_by_default(self):
        """Test keys are enabled by default"""
        from datetime import datetime
        info = APIKeyInfo(
            key_id="test",
            name="Test",
            created_at=datetime.now()
        )
        self.assertTrue(info.enabled)


if __name__ == '__main__':
    unittest.main()
