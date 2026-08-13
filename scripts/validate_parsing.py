import tempfile
import os
import textwrap
from parser import load_pipeline

GITHUB_YAML = textwrap.dedent('''
image: python:3.11
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: alpine:3.14
    steps:
      - name: Install
        run: echo installing
      - name: Use action
        uses: actions/checkout@v2
  test:
    needs: [build]
    steps:
      - run: echo testing
''')

GITLAB_YAML = textwrap.dedent('''
image: python:3.8
build_job:
  stage: build
  script:
    - echo build
test_job:
  stage: test
  needs: [build_job]
  script:
    - echo test
''')


def write_and_load(content, name):
    d = tempfile.mkdtemp()
    path = os.path.join(d, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    p = load_pipeline(path)
    print(f"Loaded pipeline from {name}: jobs={list(p.jobs.keys())}, image={p.image}")


if __name__ == '__main__':
    write_and_load(GITHUB_YAML, 'github.yml')
    write_and_load(GITLAB_YAML, 'gitlab.yml')
    print('VALIDATION-OK')
