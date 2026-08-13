import os
from runner import load_kv_file, merge_vars_into_jobs
from reporter import Reporter

class DummyJob:
    def __init__(self, env=None, needs=None):
        self.env = env or {}
        self.needs = needs or []

class DummyPipeline:
    def __init__(self, variables, jobs):
        self.variables = variables
        self.jobs = jobs


def test_var_precedence():
    pipeline = DummyPipeline(variables={'A':'1','B':'2'}, jobs={'job1': DummyJob(env={'C':'30','D':'4'})})
    extra_vars = {'B':'20','C':'3'}
    secrets = {'D':'40','E':'5'}
    merge_vars_into_jobs(pipeline, extra_vars, secrets)
    job_env = pipeline.jobs['job1'].env
    assert job_env['A'] == '1'
    assert job_env['B'] == '20'  # CLI overrides file
    assert job_env['C'] == '30'  # job overrides CLI
    assert job_env['D'] == '40'  # secret overrides job
    assert job_env['E'] == '5'   # secret added


def test_masking():
    rep = Reporter()
    obj = {'a':'hello SECRET123 world', 'nested': {'x': 'no secret', 'y': ['SECRET123','other']}}
    masked = rep._mask_secrets_in_obj(obj, ['SECRET123'])
    assert 'SECRET123' not in str(masked)
    assert masked['a'] == 'hello *** world'
    assert masked['nested']['y'][0] == '***'


def test_load_kv_file_env(tmp_path):
    p = tmp_path / 'vars.env'
    p.write_text("KEY1=val1\n#comment\nKEY2=val2\n")
    res = load_kv_file(str(p))
    assert res['KEY1'] == 'val1'
    assert res['KEY2'] == 'val2'


def test_load_kv_file_yaml(tmp_path):
    p = tmp_path / 'vars.yml'
    p.write_text("k1: v1\nk2: v2\n")
    res = load_kv_file(str(p))
    assert res['k1'] == 'v1'
    assert res['k2'] == 'v2'
