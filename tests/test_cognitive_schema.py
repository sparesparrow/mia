"""Tests for cognitive architecture FlatBuffers schemas."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCognitiveSchema(unittest.TestCase):
    """Test cognitive.fbs schema types."""

    def test_schema_file_exists(self):
        """Verify cognitive.fbs schema file exists."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "cognitive.fbs",
        )
        self.assertTrue(os.path.exists(schema_path))

    def test_schema_contains_cognitive_layer_enum(self):
        """Verify CognitiveLayer enum is defined with 7 values."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "cognitive.fbs",
        )
        with open(schema_path) as f:
            content = f.read()

        self.assertIn("enum CognitiveLayer", content)
        for layer in ["Perceptual", "Episodic", "Semantic", "Procedural",
                       "MetaCognitive", "Transfer", "Evaluative"]:
            self.assertIn(layer, content)

    def test_schema_contains_key_tables(self):
        """Verify all key tables are defined."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "cognitive.fbs",
        )
        with open(schema_path) as f:
            content = f.read()

        for table_name in ["CognitiveMessage", "KGNode", "KGEdge",
                           "CognitiveState", "InferenceResult"]:
            self.assertIn(f"table {table_name}", content)

    def test_schema_has_explicit_field_ids(self):
        """Verify all table fields have explicit (id: N) attributes."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "cognitive.fbs",
        )
        with open(schema_path) as f:
            lines = f.readlines()

        in_table = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("table "):
                in_table = True
                continue
            if in_table and stripped == "}":
                in_table = False
                continue
            if in_table and ":" in stripped and not stripped.startswith("//"):
                self.assertIn("(id:", stripped,
                              f"Missing field ID in cognitive.fbs: {stripped}")

    def test_kgnode_has_key_attribute(self):
        """Verify KGNode.id has the key attribute for sorted lookup."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "cognitive.fbs",
        )
        with open(schema_path) as f:
            content = f.read()
        self.assertIn("key", content)


class TestStorageSchema(unittest.TestCase):
    """Test storage.fbs schema types."""

    def test_schema_file_exists(self):
        """Verify storage.fbs schema file exists."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "storage.fbs",
        )
        self.assertTrue(os.path.exists(schema_path))

    def test_schema_includes_cognitive(self):
        """Verify storage.fbs includes cognitive.fbs."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "storage.fbs",
        )
        with open(schema_path) as f:
            content = f.read()
        self.assertIn('include "cognitive.fbs"', content)

    def test_schema_contains_episodic_types(self):
        """Verify episodic memory types are defined."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "storage.fbs",
        )
        with open(schema_path) as f:
            content = f.read()

        self.assertIn("table EpisodicEvent", content)
        self.assertIn("table EpisodicStore", content)
        self.assertIn("table WorkingMemoryEntry", content)
        self.assertIn("table WorkingMemoryBuffer", content)


class TestMiaSchemaFieldIds(unittest.TestCase):
    """Test that all .fbs files have explicit field IDs on table fields."""

    def _check_field_ids(self, schema_path):
        """Check that all table fields in a schema have explicit (id: N)."""
        with open(schema_path) as f:
            lines = f.readlines()

        in_table = False
        table_name = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("table "):
                in_table = True
                table_name = stripped.split()[1].rstrip("{").strip()
                continue
            if in_table and stripped == "}":
                in_table = False
                continue
            if in_table and ":" in stripped and not stripped.startswith("//"):
                self.assertIn(
                    "(id:", stripped,
                    f"Missing field ID in {os.path.basename(schema_path)}, "
                    f"table {table_name}: {stripped}"
                )

    def test_mia_fbs_has_field_ids(self):
        """All tables in mia.fbs have explicit field IDs."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "mia.fbs",
        )
        self._check_field_ids(schema_path)

    def test_vehicle_fbs_has_field_ids(self):
        """All tables in vehicle.fbs have explicit field IDs."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "protos", "vehicle.fbs",
        )
        self._check_field_ids(schema_path)

    def test_webgrab_fbs_has_field_ids(self):
        """All tables in webgrab.fbs have explicit field IDs."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "apps", "rpi-backend", "cpp-audio", "core", "webgrab.fbs",
        )
        self._check_field_ids(schema_path)

    def test_esp32_structs_in_mia_fbs(self):
        """Verify AudioFeatures and BeatEvent structs exist in mia.fbs."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "schemas", "mia.fbs",
        )
        with open(schema_path) as f:
            content = f.read()
        self.assertIn("struct AudioFeatures", content)
        self.assertIn("struct BeatEvent", content)


if __name__ == "__main__":
    unittest.main()
