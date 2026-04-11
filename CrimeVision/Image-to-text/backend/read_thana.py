
import sys
import io

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def read_search():
    try:
        with open('f:/Image-to-text/backend/thana_search.txt', 'rt', encoding='utf-16', errors='replace') as f:
            content = f.read()
            lines = content.splitlines()
            for line in lines:
                if 'Text:' in line:
                    print(line)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    read_search()
