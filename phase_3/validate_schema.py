
import json
import jsonschema
import sys

def validate_schema():
    print("🔍 Validating Phase 3 Semantics JSON against Schema...")
    
    try:
        with open("phase_3/schemas/lighting_semantics_knowledge_schema.json", "r") as f:
            schema = json.load(f)
            
        with open("phase_3/knowledge/semantics/baseline_semantics.json", "r") as f:
            data = json.load(f)
            
        # Validate each item in the list against the schema
        if isinstance(data, list):
            for i, item in enumerate(data):
                try:
                    jsonschema.validate(instance=item, schema=schema)
                except jsonschema.exceptions.ValidationError as e:
                    print(f"❌ Error in Rule #{i}: {e.message}")
                    return False
        else:
             jsonschema.validate(instance=data, schema=schema)

        print("✅ SUCCESS: baseline_semantics.json is fully compliant with the new Schema.")
        return True
        
    except Exception as e:
        print(f"❌ critical validation error: {e}")
        return False

if __name__ == "__main__":
    if not validate_schema():
        sys.exit(1)
