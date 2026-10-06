# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Execute tag-name and UTC calendar period regressions and artifact contracts."""
import copy
import importlib.util
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


reg = module('page_period_regressions', 'test-review-regressions.py')
publication = module('page_period_publication', 'test-publication-review.py')
pages = module('page_period_pages', 'test-pages-publication.py')


def main():
    publication.workflow_contract()
    explorer = {'pipeline.yaml': {'stages': [{'input': {'id': 1}, 'output': {'id': 1}}]}}
    pages.check_explorer_values('fixture', explorer)
    for field in ('input', 'output'):
        incomplete = copy.deepcopy(explorer)
        del incomplete['pipeline.yaml']['stages'][0][field]
        try:
            pages.check_explorer_values('fixture', incomplete)
        except AssertionError:
            pass
        else:
            raise AssertionError(f'missing {field} did not fail the publication gate')
    directory = ROOT / '.conformance' / f'pages-periods-{time.time_ns()}'
    directory.mkdir(parents=True)
    suite = reg.Suite(directory, {})
    try:
        html = '<title>Chart</title><meta name="description" content="Summary"><h1>Chart</h1><img alt="Chart"><meta name="viewport">'
        for variant in ('cli', 'mcp'):
            cfg = reg.config('workflows/seo-pipeline', variant)
            for tag in ('script-loader', 'style-guide', 'textarea-box', 'xmp-player', 'iframe-card', 'noembed-box', 'noframes-panel', 'plaintext-widget'):
                result = suite.execute(cfg, {'html': f'<{tag}></{tag}>' + html})
                assert result['analysis']['score'] == 100 and result['analysis']['image_count'] == 1, result
            result = suite.execute(cfg, {'html': '<title>Chart</title><h1>Chart</h1><meta-description name="description" content="Fake"><meta-viewport name="viewport"><img-loader src=x>'})
            assert result['analysis']['score'] == 60 and result['analysis']['image_count'] == 0 and not result['analysis']['has_viewport'], result
            result = suite.execute(cfg, {'html': '<title-widget>Fake</title-widget><h1>Chart</h1><meta name="description" content="Summary"><meta name="viewport">'})
            assert result['analysis']['title'] == '' and result['analysis']['score'] == 75, result
            result = suite.execute(cfg, {'html': '<script >const x="<meta name=viewport><img>";</script>' + html})
            assert result['analysis']['score'] == 100 and result['analysis']['image_count'] == 1, result
            cfg = reg.config('workflows/stripe-reports', variant)
            initialization = next(processor['try'] for processor in cfg['pipeline']['processors'] if 'try' in processor)
            for timestamp in ('2026-10-06T15:00:00+00:00', '2026-10-07T00:00:00+00:00', '2024-03-01T00:01:00+00:00'):
                now = datetime.fromisoformat(timestamp)
                clock = int(now.timestamp())
                day_start = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                for period, start, end in (('today', day_start, clock), ('yesterday', day_start - 86400, day_start - 1), ('week', clock - 604800, clock)):
                    processors = copy.deepcopy(initialization[:2])
                    processors[0]['mapping'] = processors[0]['mapping'].replace('now().ts_unix()', str(clock))
                    processors.append({'mapping': 'root = {"url": meta("stripe_url")} '})
                    fixture = {'_source_pipeline': cfg['_source_pipeline'], 'pipeline': {'processors': processors}}
                    result = suite.execute(fixture, {'period': period})
                    query = parse_qs(urlsplit(result['url']).query)
                    assert query['created[gte]'] == [str(start)], (variant, period, timestamp, query)
                    assert query['created[lte]'] == [str(end)], (variant, period, timestamp, query)
        reg.write_evidence()
        print(f'PASS {len(reg.EVIDENCE)} tag-name and calendar-boundary executions')
    finally:
        suite.close()


if __name__ == '__main__':
    main()
