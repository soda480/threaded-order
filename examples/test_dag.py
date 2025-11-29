import time
import random
from faker import Faker
from threaded_order import dmark, ThreadProxyLogger

logger = ThreadProxyLogger()


def setup_state(state):
    state.update({
        'faker': Faker()
    })


def run(name, state, deps=None, fail=False):
    with state['_state_lock']:
        last_name = state['faker'].last_name()
    sleep = random.uniform(18, 40)
    logger.debug(f'{name} "{last_name}" running - sleeping {sleep:.2f}s')
    time.sleep(sleep)
    if fail:
        assert False, 'Intentional Failure'
    else:
        results = []
        for dep in (deps or []):
            dep_result = state.get(dep, '--no-result--')
            results.append(f'{name}.{dep_result}')
        if not results:
            results.append(name)
        logger.info(f'{name} passed')
        state[name] = '|'.join(results)


# ---------------------------------------------------------------------------
# Layer 1 (9 tests)
#   - test_01_03 has 4 children (layer2)
#   - test_01_06 has 2 children (layer2)
#   - test_01_08 has 3 children (layer2)
# ---------------------------------------------------------------------------

@dmark(with_state=True, tag='layer1')
def test_01_01(state): return run('test_01_01', state)


@dmark(with_state=True, tag='layer1')
def test_01_02(state): return run('test_01_02', state)


# parent of 4 children in layer2
@dmark(with_state=True, tag='layer1')
def test_01_03(state): return run('test_01_03', state)


@dmark(with_state=True, tag='layer1')
def test_01_04(state): return run('test_01_04', state)


@dmark(with_state=True, tag='layer1')
def test_01_05(state): return run('test_01_05', state)


# parent of 2 children in layer2
@dmark(with_state=True, tag='layer1')
def test_01_06(state): return run('test_01_06', state)


@dmark(with_state=True, tag='layer1')
def test_01_07(state): return run('test_01_07', state)


# parent of 3 children in layer2
@dmark(with_state=True, tag='layer1')
def test_01_08(state): return run('test_01_08', state)


@dmark(with_state=True, tag='layer1')
def test_01_09(state): return run('test_01_09', state)


# ---------------------------------------------------------------------------
# Layer 2 (9 tests)
#   - children of test_01_03: 02_01, 02_02, 02_03, 02_04
#   - children of test_01_06: 02_05, 02_06
#   - children of test_01_08: 02_07, 02_08, 02_09
#   - test_02_02 has 3 children (layer3)
#   - test_02_06 has 2 children (layer3)
#   - test_02_08 has 2 children (layer3)
# ---------------------------------------------------------------------------

@dmark(with_state=True, after=['test_01_03'], tag='layer2')
def test_02_01(state): return run('test_02_01', state, deps=['test_01_03'])


# parent of 3 children in layer3
@dmark(with_state=True, after=['test_01_03'], tag='layer2')
def test_02_02(state): return run('test_02_02', state, deps=['test_01_03'])


@dmark(with_state=True, after=['test_01_03'], tag='layer2')
def test_02_03(state): return run('test_02_03', state, deps=['test_01_03'])


@dmark(with_state=True, after=['test_01_03'], tag='layer2')
def test_02_04(state): return run('test_02_04', state, deps=['test_01_03'])


@dmark(with_state=True, after=['test_01_06'], tag='layer2')
def test_02_05(state): return run('test_02_05', state, deps=['test_01_06'])


# parent of 2 children in layer3
@dmark(with_state=True, after=['test_01_06'], tag='layer2')
def test_02_06(state): return run('test_02_06', state, deps=['test_01_06'])


@dmark(with_state=True, after=['test_01_08'], tag='layer2')
def test_02_07(state): return run('test_02_07', state, deps=['test_01_08'])


# parent of 2 children in layer3
@dmark(with_state=True, after=['test_01_08'], tag='layer2')
def test_02_08(state): return run('test_02_08', state, deps=['test_01_08'])


@dmark(with_state=True, after=['test_01_08'], tag='layer2')
def test_02_09(state): return run('test_02_09', state, deps=['test_01_08'])


# ---------------------------------------------------------------------------
# Layer 3 (8 tests)
#   - children of test_02_02: 03_01, 03_02, 03_03
#   - children of test_02_06: 03_04, 03_05
#   - children of test_02_08: 03_06, 03_07
#   - 03_08 is child of 02_04
#   - test_03_01 has 3 children (layer4)
#   - test_03_04 has 1 child (layer4)
#   - test_03_07 has 1 child (layer4)
# ---------------------------------------------------------------------------

# parent of 3 children in layer4
@dmark(with_state=True, after=['test_02_02'], tag='layer3')
def test_03_01(state): return run('test_03_01', state, deps=['test_02_02'])


@dmark(with_state=True, after=['test_02_02'], tag='layer3')
def test_03_02(state): return run('test_03_02', state, deps=['test_02_02'])


@dmark(with_state=True, after=['test_02_02'], tag='layer3')
def test_03_03(state): return run('test_03_03', state, deps=['test_02_02'])


# parent of 1 child in layer4
@dmark(with_state=True, after=['test_02_06'], tag='layer3')
def test_03_04(state): return run('test_03_04', state, deps=['test_02_06'])


@dmark(with_state=True, after=['test_02_06'], tag='layer3')
def test_03_05(state): return run('test_03_05', state, deps=['test_02_06'])


@dmark(with_state=True, after=['test_02_08'], tag='layer3')
def test_03_06(state): return run('test_03_06', state, deps=['test_02_08'])


# parent of 1 child in layer4
@dmark(with_state=True, after=['test_02_08'], tag='layer3')
def test_03_07(state): return run('test_03_07', state, deps=['test_02_08'])


@dmark(with_state=True, after=['test_02_04'], tag='layer3')
def test_03_08(state): return run('test_03_08', state, deps=['test_02_04'])


# ---------------------------------------------------------------------------
# Layer 4 (5 tests)
#   - children of test_03_01: 04_01, 04_02, 04_03
#   - child of test_03_04: 04_04
#   - child of test_03_07: 04_05
#   - test_04_02 has 2 children (layer5)
# ---------------------------------------------------------------------------

@dmark(with_state=True, after=['test_03_01'], tag='layer4')
def test_04_01(state): return run('test_04_01', state, deps=['test_03_01'])


# parent of 2 children in layer5
@dmark(with_state=True, after=['test_03_01'], tag='layer4')
def test_04_02(state): return run('test_04_02', state, deps=['test_03_01'])


@dmark(with_state=True, after=['test_03_01'], tag='layer4')
def test_04_03(state): return run('test_04_03', state, deps=['test_03_01'])


@dmark(with_state=True, after=['test_03_04'], tag='layer4')
def test_04_04(state): return run('test_04_04', state, deps=['test_03_04'])


@dmark(with_state=True, after=['test_03_07'], tag='layer4')
def test_04_05(state): return run('test_04_05', state, deps=['test_03_07'])


# ---------------------------------------------------------------------------
# Layer 5 (3 tests)
#   - children of test_04_02: 05_01, 05_02
#   - 05_03 is child of 04_04
#   - test_05_02 has 1 child (layer6)
# ---------------------------------------------------------------------------

@dmark(with_state=True, after=['test_04_02'], tag='layer5')
def test_05_01(state): return run('test_05_01', state, deps=['test_04_02'])


# parent of 1 child in layer6
@dmark(with_state=True, after=['test_04_02'], tag='layer5')
def test_05_02(state): return run('test_05_02', state, deps=['test_04_02'])


@dmark(with_state=True, after=['test_04_04'], tag='layer5')
def test_05_03(state): return run('test_05_03', state, deps=['test_04_04'])


# ---------------------------------------------------------------------------
# Layer 6 (1 test)
#   - child of test_05_02: 06_01
# ---------------------------------------------------------------------------

@dmark(with_state=True, after=['test_05_02'], tag='layer6')
def test_06_01(state): return run('test_06_01', state, deps=['test_05_02'])
