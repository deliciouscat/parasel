# Pipeline Patterns

## Sequential Processing (Serial)

**Pattern**: Chain operations that depend on previous results.

**Structure**:
```python
from parasel import Serial, ModuleAdapter

pipeline = Serial([
    ModuleAdapter(step1, out_name="result1"),
    ModuleAdapter(step2, out_name="result2"),  # uses result1
    ModuleAdapter(step3, out_name="final")     # uses result2
])
```

**Example: Text processing pipeline**
```python
def clean_text(context: Context, out_name: str, **kwargs):
    text = context.get("input_text")
    cleaned = text.strip().lower()
    context[out_name] = cleaned

def tokenize(context: Context, out_name: str, **kwargs):
    text = context.get("cleaned")
    tokens = text.split()
    context[out_name] = tokens

def count_words(context: Context, out_name: str, **kwargs):
    tokens = context.get("tokens")
    count = len(tokens)
    context[out_name] = count

pipeline = Serial([
    ModuleAdapter(clean_text, out_name="cleaned"),
    ModuleAdapter(tokenize, out_name="tokens"),
    ModuleAdapter(count_words, out_name="word_count")
])
```

## Independent Parallel Processing (Parallel)

**Pattern**: Execute operations concurrently when they don't depend on each other.

**Structure**:
```python
from parasel import Parallel, ModuleAdapter

pipeline = Parallel([
    ModuleAdapter(task_a, out_name="result_a"),
    ModuleAdapter(task_b, out_name="result_b"),
    ModuleAdapter(task_c, out_name="result_c")
])
```

**Example: Data validation checks**
```python
def check_format(context: Context, out_name: str, **kwargs):
    data = context.get("input_data")
    valid = validate_format(data)
    context[out_name] = valid

def check_schema(context: Context, out_name: str, **kwargs):
    data = context.get("input_data")
    valid = validate_schema(data)
    context[out_name] = valid

def check_business_rules(context: Context, out_name: str, **kwargs):
    data = context.get("input_data")
    valid = validate_rules(data)
    context[out_name] = valid

pipeline = Parallel([
    ModuleAdapter(check_format, out_name="format_valid"),
    ModuleAdapter(check_schema, out_name="schema_valid"),
    ModuleAdapter(check_business_rules, out_name="rules_valid")
])
```

## Same Function, Different Arguments (ByArgs)

**Pattern**: Execute the same function multiple times with different parameter values in parallel.

**Structure**:
```python
from parasel import Parallel, ByArgs, ModuleAdapter

node = ModuleAdapter(my_function, out_name="results")

pipeline = Parallel([
    ByArgs(node, args={"param": ["value1", "value2", "value3"]})
])
# Executes: my_function(param="value1"), my_function(param="value2"), my_function(param="value3")
# context["results"] = [result1, result2, result3]
```

**Example: Multi-model inference**
```python
async def llm_call(context: Context, model: str, out_name: str, **kwargs):
    prompt = context.get("prompt")
    response = await llm_api(prompt, model=model)
    context[out_name] = response

llm_node = ModuleAdapter(llm_call, out_name="llm_responses")

pipeline = Parallel([
    ByArgs(llm_node, args={"model": ["gpt-4", "claude-3", "gemini-pro"]})
])
# context["llm_responses"] = [gpt4_response, claude_response, gemini_response]
```

**Example: Batch file processing**
```python
def process_file(context: Context, file_path: str, out_name: str, **kwargs):
    data = read_file(file_path)
    processed = transform(data)
    context[out_name] = processed

process_node = ModuleAdapter(process_file, out_name="processed_files")

pipeline = Parallel([
    ByArgs(process_node, args={"file_path": ["file1.txt", "file2.txt", "file3.txt"]})
])
```

## Dynamic List Processing (ByKeys)

**Pattern**: Process each item in a Context list with the same function in parallel.

**Structure**:
```python
from parasel import Serial, Parallel, ByKeys, ModuleAdapter

# Step 1: Generate list
generate_list = ModuleAdapter(create_items, out_name="items")
# context["items"] = ["item1", "item2", "item3"]

# Step 2: Process each item
process = ModuleAdapter(process_item, out_name="processed")

pipeline = Serial([
    generate_list,
    Parallel([
        ByKeys(process, keys=["items"], input_key_name="item")
    ])
])
# context["processed"] = [processed1, processed2, processed3]
```

**Example: Query expansion and search**
```python
async def expand_query(context: Context, out_name: str, **kwargs):
    query = context.get("query")
    expanded = await llm_expand(query)  # Returns ["query1", "query2", "query3"]
    context[out_name] = expanded

async def web_search(context: Context, query: str, out_name: str, **kwargs):
    results = await search_api(query)
    context[out_name] = results

expand_node = ModuleAdapter(expand_query, out_name="expanded_queries")
search_node = ModuleAdapter(web_search, out_name="search_results")

pipeline = Serial([
    expand_node,
    Parallel([
        ByKeys(search_node, keys=["expanded_queries"], input_key_name="query")
    ])
])
```

**Example: Batch API calls**
```python
async def fetch_user_data(context: Context, user_id: str, out_name: str, **kwargs):
    data = await api.get_user(user_id)
    context[out_name] = data

fetch_node = ModuleAdapter(fetch_user_data, out_name="user_data")

# context["user_ids"] = ["user1", "user2", "user3"] (from previous step)
pipeline = Parallel([
    ByKeys(fetch_node, keys=["user_ids"], input_key_name="user_id")
])
```

## Combining Patterns

**Pattern**: Combine Serial, Parallel, ByArgs, and ByKeys for complex workflows.

**Example: Multi-language search system**
```python
# Expand query in multiple languages (ByArgs)
# Then search each expansion (ByKeys)
# Finally merge and rank results

async def expand_query(context: Context, language: str, out_name: str, **kwargs):
    query = context.get("query")
    expanded = await llm_translate_and_expand(query, language)
    context[out_name] = expanded

async def search(context: Context, query: str, out_name: str, **kwargs):
    results = await search_api(query)
    context[out_name] = results

def merge_and_rank(context: Context, out_name: str, **kwargs):
    all_results = context.get("all_results", [])
    merged = deduplicate(flatten(all_results))
    ranked = rank_by_relevance(merged)
    context[out_name] = ranked

expand_node = ModuleAdapter(expand_query, out_name="expansions")
flatten_node = ModuleAdapter(flatten_list, out_name="expansions")
search_node = ModuleAdapter(search, out_name="all_results")
merge_node = ModuleAdapter(merge_and_rank, out_name="final_results")

pipeline = Serial([
    Parallel([
        ByArgs(expand_node, args={"language": ["en", "ko", "ja"]})
    ]),
    flatten_node,
    Parallel([
        ByKeys(search_node, keys=["expansions"], input_key_name="query")
    ]),
    merge_node
])
```

**Example: Batch data processing**
```python
def load_data_sources(context: Context, out_name: str, **kwargs):
    sources = ["db1", "db2", "db3"]
    context[out_name] = sources

async def fetch_data(context: Context, source: str, out_name: str, **kwargs):
    data = await database_query(source)
    context[out_name] = data

def aggregate(context: Context, out_name: str, **kwargs):
    all_data = context.get("fetched_data", [])
    combined = merge_datasets(all_data)
    context[out_name] = combined

load_node = ModuleAdapter(load_data_sources, out_name="sources")
fetch_node = ModuleAdapter(fetch_data, out_name="fetched_data")
agg_node = ModuleAdapter(aggregate, out_name="result")

pipeline = Serial([
    load_node,
    Parallel([
        ByKeys(fetch_node, keys=["sources"], input_key_name="source")
    ]),
    agg_node
])
```
