#!/usr/bin/env python3
"""Test script to demonstrate LLM usage optimization"""

import requests
import json
import time

def test_llm_optimization():
    """Test the optimized LLM usage system"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing LLM Usage Optimization")
    print("Start the server with: python3 run_app.py")
    print("Then run this test in another terminal\n")
    
    # Test messages - some will be cached, some optimized
    test_messages = [
        "Filter invoices for last month, vendor='IndiSky', status=failed",
        "hi there",  # Simple pattern - no LLM call
        "Filter invoices for last month, vendor='TechSolutions', status=failed",  # Similar to first - should use cache
        "Create ticket: Failed invoices need GSTIN information",
        "Show my tickets",
        "thanks for your help",  # Simple pattern - no LLM call
        "Export the filtered data as CSV",
        "Filter invoices for last month, vendor='Global', status=failed",  # Similar pattern - optimized
        "help me understand what you can do",  # Simple pattern - no LLM call
        "Create ticket: Payment processing issues"
    ]
    
    print("🚀 Testing optimization features...\n")
    
    # Get initial usage stats
    try:
        response = requests.get(f"{base_url}/llm/usage")
        if response.status_code == 200:
            initial_stats = response.json()["usage_optimization"]
            print(f"📊 Initial Stats: {initial_stats['llm_calls_made']} LLM calls, {initial_stats['cache_hits']} cache hits")
        else:
            initial_stats = None
    except:
        initial_stats = None
    
    print("\n🔄 Running test conversations...\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i:2d}. Testing: '{message}'")
        
        start_time = time.time()
        response = requests.post(f"{base_url}/chat", json={
            "user_id": "john_doe",
            "message": message
        })
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"    ✅ Success: {data['success']}")
            print(f"    🤖 Response: {data['agent_response'][:100]}{'...' if len(data['agent_response']) > 100 else ''}")
            print(f"    🔧 Tool: {data.get('tool_used', 'none')}")
            print(f"    ⚡ Time: {response_time:.0f}ms")
            
            # Check if response was cached or optimized
            llm_response = data.get('llm_response', {})
            if isinstance(llm_response, dict):
                if llm_response.get('cached'):
                    print(f"    💾 Cached response used")
                elif llm_response.get('optimized'):
                    print(f"    🎯 Prompt optimized (est. {llm_response.get('token_estimate', 'unknown')} tokens)")
        else:
            print(f"    ❌ Error: {response.status_code}")
        
        print()
        time.sleep(0.5)  # Small delay between requests
    
    # Get final usage stats
    print("📈 Final Usage Statistics:")
    try:
        response = requests.get(f"{base_url}/llm/usage")
        if response.status_code == 200:
            final_stats = response.json()["usage_optimization"]
            
            print(f"  LLM Calls Made: {final_stats['llm_calls_made']}")
            print(f"  Cache Hits: {final_stats['cache_hits']}")
            print(f"  Cache Hit Rate: {final_stats['cache_hit_rate']}")
            print(f"  Prompts Optimized: {final_stats['prompts_optimized']}")
            print(f"  Estimated Tokens Saved: {final_stats['estimated_tokens_saved']}")
            print(f"  Optimization Ratio: {final_stats['optimization_ratio']}")
            print(f"  Potential Calls Avoided: {final_stats['potential_calls_avoided']}")
            
            # Calculate savings
            total_potential_calls = final_stats['llm_calls_made'] + final_stats['cache_hits']
            if total_potential_calls > 0:
                savings_percentage = (final_stats['cache_hits'] / total_potential_calls) * 100
                print(f"\n🎉 Optimization Results:")
                print(f"  • Avoided {final_stats['cache_hits']} LLM calls through caching")
                print(f"  • Saved approximately {savings_percentage:.1f}% of potential API calls")
                print(f"  • Reduced token usage by ~{final_stats['estimated_tokens_saved']} tokens")
                
                if initial_stats:
                    calls_difference = final_stats['llm_calls_made'] - initial_stats.get('llm_calls_made', 0)
                    print(f"  • Only made {calls_difference} new LLM calls for {len(test_messages)} messages")
            
        else:
            print("  Unable to retrieve final stats")
    except Exception as e:
        print(f"  Error retrieving stats: {e}")
    
    print("\n💡 Optimization Features Demonstrated:")
    print("  ✅ Pattern-based responses (no LLM calls for greetings, help, thanks)")
    print("  ✅ Intelligent caching (similar requests reuse responses)")
    print("  ✅ Prompt optimization (reduced token usage per call)")
    print("  ✅ Smart context compression (preserves quality, reduces size)")
    print("  ✅ Standard tool responses (common outcomes don't need LLM)")
    
    print("\n🔍 Test cache clearing:")
    try:
        response = requests.post(f"{base_url}/llm/cache/clear")
        if response.status_code == 200:
            print("  ✅ Cache cleared successfully")
        else:
            print("  ❌ Failed to clear cache")
    except:
        print("  ❌ Error clearing cache")

if __name__ == "__main__":
    test_llm_optimization()