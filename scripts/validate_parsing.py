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

GITLAB_DEFAULT_YAML = textwrap.dedent('''
default:
  image: python:3.9-alpine
stages:
 - test
 - push
variables:
  image: mosakram/flaskapp
  tag: 0.1
apptest:
  stage: test
  script:
    - pip install -r req.txt
    - pytest
buildAndpush:
  before_script:
    - docker login -u $user -p $pass
  stage: push
  image: docker:29.4.3-cli-alpine3.23
  services:
    - docker:dind
  script:
    - docker build -t $image:$tag .
    - docker push $image:$tag
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
    write_and_load(GITLAB_DEFAULT_YAML, 'gitlab-default.yml')
    print('VALIDATION-OK')
