"""
Example usage of YandexGPT LLM tasks.
"""
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.yandex_llm_tasks import (
    test_yandex_connection,
    generate_student_feedback
)
from worker.test_data import (
    get_test_student_data
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_student_feedback():
    """Example: Generate feedback for a student."""
    print("\n" + "="*60)
    print("EXAMPLE: Student Feedback Generation")
    print("="*60)
    
    # Get test data for student id_40
    student_data = get_test_student_data("id_40")
    
    print(f"Student data contains {len(student_data)} activities")
    print("Sample activities:")
    for i, activity in enumerate(student_data[:3]):
        print(f"  {i+1}. {activity['Название']} - {activity['Статус']}")
    
    # Generate feedback using YandexGPT Pro
    print("\nGenerating feedback using YandexGPT Pro...")
    result = generate_student_feedback.delay(
        student_id="id_40",
        student_data=student_data,
        model_type="yandexgpt"
    )
    
    feedback = result.get(timeout=120)
    
    if feedback:
        print("\nGenerated Feedback:")
        print(f"  Activity Score: {feedback.get('activity', 'N/A')}/10")
        print(f"  Homework Score: {feedback.get('homework', 'N/A')}/10")
        print(f"  Tests Score: {feedback.get('tests', 'N/A')}/10")
        print(f"  Advice: {feedback.get('advice', 'N/A')}")
    else:
        print("Failed to generate feedback")


def example_connection_test():
    """Example: Test connection to Yandex Cloud."""
    print("\n" + "="*60)
    print("EXAMPLE: Connection Test")
    print("="*60)
    
    print("Testing connection to Yandex Cloud ML SDK...")
    result = test_yandex_connection.delay()
    
    connection_result = result.get(timeout=60)
    
    if connection_result:
        print("\nConnection Test Results:")
        print(f"  SDK Initialized: {connection_result.get('sdk_initialized', False)}")
        print(f"  Models Available: {connection_result.get('models_available', {})}")
        print(f"  Success: {connection_result.get('success', False)}")
        
        if connection_result.get('test_response'):
            print(f"  Test Response: {connection_result['test_response'][:100]}...")
        
        if connection_result.get('error'):
            print(f"  Error: {connection_result['error']}")
    else:
        print("Failed to test connection")


def main():
    """Run all examples."""
    print("YandexGPT LLM Tasks Examples")
    print(f"Started at: {datetime.now()}")
    
    # Check if environment variables are set
    folder_id = os.getenv("YANDEX_CLOUD_FOLDER_ID")
    api_key = os.getenv("YANDEX_CLOUD_API_KEY")
    
    if not folder_id or not api_key:
        print("\n" + "="*60)
        print("ERROR: Yandex Cloud credentials not found!")
        print("Please set environment variables:")
        print("  YANDEX_CLOUD_FOLDER_ID=your_folder_id")
        print("  YANDEX_CLOUD_API_KEY=your_api_key")
        print("="*60)
        return
    
    try:
        # Test connection first
        example_connection_test()
        
        # Run examples
        example_student_feedback()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print(f"Finished at: {datetime.now()}")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"\nExample failed: {e}")
        raise


if __name__ == "__main__":
    main()
