"""
Multi-Language Processing Example

Demonstrates ByArgs for parallel execution with different arguments.
"""

import sys
from pathlib import Path

parasel_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parasel_path))

from parasel import Serial, Parallel, ByArgs, ModuleAdapter
from parasel.core.context import Context


def translate_greeting(context: Context, language: str, out_name: str, **kwargs):
    """Translate greeting to specified language"""
    greetings = {
        "en": "Hello, World!",
        "ko": "안녕하세요, 세계!",
        "ja": "こんにちは、世界!",
        "zh": "你好，世界!",
        "es": "¡Hola, Mundo!",
    }
    
    result = greetings.get(language, "Hello, World!")
    print(f"[{language.upper()}] {result}")
    context[out_name] = result


def flatten_list(context: Context, out_name: str, in_name: str = None, **kwargs):
    """Flatten nested list results"""
    key = in_name if in_name else out_name
    results = context.get(key, [])
    
    if isinstance(results, list) and results and isinstance(results[0], list):
        flat = [item for sublist in results for item in sublist]
    else:
        flat = results
    
    context[out_name] = flat


def main():
    print("=" * 60)
    print("Multi-Language Processing Example")
    print("=" * 60)
    
    # Node for translation
    translate_node = ModuleAdapter(translate_greeting, out_name="translations")
    
    # Pipeline: Translate greeting into multiple languages
    pipeline = Serial([
        Parallel([
            ByArgs(translate_node, args={"language": ["en", "ko", "ja", "zh", "es"]})
        ]),
        # Results are accumulated in list
    ])
    
    # Execute
    context = Context({}, thread_safe=True)
    print("\nTranslating 'Hello, World!' to multiple languages...\n")
    
    pipeline.run(context)
    
    print(f"\n{'=' * 60}")
    print("All Translations:")
    for i, translation in enumerate(context["translations"], 1):
        print(f"  {i}. {translation}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
