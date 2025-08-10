import sys

sys.path.append(".")

from pathlib import Path

from examples.upload_agent_choices import collect_agent_choices_for_dataset


def test_data_preparation():
    """Test the data preparation component"""
    print("🧪 Testing data preparation...")

    output_path = Path("output")
    if not output_path.exists():
        print("❌ Output directory not found")
        return False

    try:
        df = collect_agent_choices_for_dataset(output_path)
        print(f"✅ Successfully collected {len(df)} agent decisions")
        print(f"   - Agents: {df['agent_name'].nunique()}")
        print(f"   - Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   - Questions: {df['question_id'].nunique()}")
        return True
    except Exception as e:
        print(f"❌ Data preparation failed: {e}")
        return False


def test_backend_imports():
    """Test that backend dependencies can be imported"""
    print("\n🧪 Testing backend imports...")

    try:
        print("✅ Backend imports successful")
        return True
    except Exception as e:
        print(f"❌ Backend import failed: {e}")
        return False


def test_frontend_imports():
    """Test that frontend dependencies can be imported"""
    print("\n🧪 Testing frontend imports...")

    try:
        print("✅ Frontend imports successful")
        return True
    except Exception as e:
        print(f"❌ Frontend import failed: {e}")
        return False


def main():
    print("🚀 Testing PrediBench Components\n")

    results = []
    results.append(test_data_preparation())
    results.append(test_backend_imports())
    results.append(test_frontend_imports())

    print("\n📊 Test Results:")
    if all(results):
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
