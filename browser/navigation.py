"""Seven stages using the case's original submission gates."""
KEYS = ('cl','li','ra','an','di')

def frontier(state):
    return state['stage']


def can_advance(state):
    stage = state['stage']
    return stage == 0 or (1 <= stage <= 5 and KEYS[stage - 1] in state['submissions'])
