import sys
sys.path.append('backend/app/services')
sys.path.append('backend/app/core')

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from query import answer_query
import json

def test():
    db = SessionLocal()
    
    test_questions = [
        "What is the maximum probation period allowed?",
        "How many days of annual leave is an employee entitled to?",
        "What are the notice period requirements for resignation?"
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        result = answer_query(question, db)
        
        print(f"\n📋 ANSWER:")
        print(result['answer'])
        
        print(f"\n📎 CITATIONS:")
        for cite in result['citations']:
            print(f"  • {cite['article']}: {cite['relevant_text'][:100]}...")
        
        print(f"\n📊 Confidence: {result['confidence']}")
        print(f"⏱️  Latency: {result['latency_ms']}ms")
        
        if result.get('limitations'):
            print(f"⚠️  Limitations: {result['limitations']}")
        
        print()
    
    db.close()

if __name__ == "__main__":
    test()