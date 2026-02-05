"""
Web Recommendation Pipeline Example

Real-world example: Query expansion → Search → Scoring
Based on /Users/deliciouscat/projects/WizPerch-ai-pipeline/
"""

import sys
from pathlib import Path

parasel_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parasel_path))

from parasel import Serial, Parallel, ByArgs, ByKeys, ModuleAdapter
from parasel.core.context import Context


# Mock implementations (replace with real APIs)
def expand_query_mock(query: str, language: str) -> list:
    """Mock query expansion"""
    if language == "en":
        return [f"{query}", f"{query} guide", f"best {query}"]
    else:
        return [f"{query} (ko)", f"{query} 가이드", f"최고 {query}"]


def search_mock(query: str) -> list:
    """Mock search results"""
    return [
        {"title": f"Result for '{query}'", "url": f"http://example.com/{query}", "score": 0.9},
        {"title": f"Guide to {query}", "url": f"http://example.com/guide-{query}", "score": 0.8},
    ]


# Pipeline functions
def query_expansion_by_language(context: Context, language: str, out_name: str, **kwargs):
    """Expand query in specified language"""
    query = context.get("query", "")
    expanded = expand_query_mock(query, language)
    print(f"[Expand-{language}] {query} → {expanded}")
    context[out_name] = expanded


def duckduckgo_search(context: Context, input: str, out_name: str, **kwargs):
    """Search for a query"""
    results = search_mock(input)
    print(f"[Search] '{input}' → {len(results)} results")
    context[out_name] = results


def normalize_scoring(context: Context, out_name: str, **kwargs):
    """Score and rank results"""
    all_results = context.get("duckduckgo_search", [])
    
    # Flatten nested results
    flat_results = []
    for item in all_results:
        if isinstance(item, list):
            flat_results.extend(item)
        else:
            flat_results.append(item)
    
    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for result in flat_results:
        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)
    
    # Sort by score
    scored = sorted(unique_results, key=lambda x: x["score"], reverse=True)
    
    print(f"[Score] {len(flat_results)} results → {len(scored)} unique, sorted")
    context[out_name] = scored


def flatten_list(context: Context, out_name: str, in_name: str = None, **kwargs):
    """Flatten nested lists"""
    key = in_name if in_name else out_name
    results = context.get(key, [])
    
    if isinstance(results, list) and results and isinstance(results[0], list):
        flat = [item for sublist in results for item in sublist]
    else:
        flat = results
    
    context[out_name] = flat


def main():
    print("=" * 60)
    print("Web Recommendation Pipeline")
    print("=" * 60)
    
    # Build pipeline
    query_expansion = ModuleAdapter(query_expansion_by_language, out_name="query_expansion")
    flatten_queries = ModuleAdapter(flatten_list, out_name="query_expansion")
    
    search = ModuleAdapter(duckduckgo_search, out_name="duckduckgo_search")
    flatten_results = ModuleAdapter(flatten_list, out_name="duckduckgo_search", in_name="duckduckgo_search")
    
    scoring = ModuleAdapter(normalize_scoring, out_name="scored_results")
    
    pipeline = Serial([
        # 1. Expand query in English and Korean
        Parallel([
            ByArgs(query_expansion, args={"language": ["en", "ko"]})
        ]),
        flatten_queries,
        
        # 2. Search each expanded query
        Parallel([
            ByKeys(search, keys=["query_expansion"], input_key_name="input")
        ]),
        flatten_results,
        
        # 3. Score and rank
        scoring,
    ]).expose(expose_keys=["scored_results"])
    
    # Execute
    context = Context({"query": "python tutorial"}, thread_safe=True)
    
    print(f"\nInput Query: {context['query']}")
    print("\nExecuting pipeline...\n")
    
    pipeline.run(context)
    
    print(f"\n{'=' * 60}")
    print("Final Results:")
    for i, result in enumerate(context["scored_results"][:5], 1):
        print(f"  {i}. {result['title']}")
        print(f"     {result['url']} (score: {result['score']})")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
