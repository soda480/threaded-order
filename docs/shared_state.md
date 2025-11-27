
# State Concurrency Rules

`state` is a shared dictonary available to all worker threads.

Follow these rules to keep everythng safe and predictable:

## 1. Read-Only -> always safe

If a task only reads from `state`, you're good.
```Python
value = state['config']['endpoint']
```
No lock needed.

## 2. One writer per key -> safe

If only one task ever writes to a key, and dependencies enforce the order, you don’t need a lock.
```Python
@s.dregister(with_state=True)
def load(state):
    state['x'] = 10

@s.dregister(after=['load'], with_state=True)
def compute(state):
    state['x'] += 5
```
No overlap -> no race.

## 3. Shared mutation -> use the lock

If multiple tasks might touch the same key or mutate the same object, use the shared lock:
```Python
lock = state['_state_lock']
with lock:
    state['counter'] = state.get('counter', 0) + 1
```

Or for collections:
```Python
with state['_state_lock']:
    state['items'].append('a')
```

## 4. Don't modify reserved keys

These keys are owned by the scheduler:
 * `state['results']` → scheduler writes task results
 * `state['_state_lock']` → shared lock for safe writes

You may read from `state['results']` in workers.

## Summary
* Read-only? Safe.
* One task writes a key? Safe.
* More than one task writes or mutates? Use `_state_lock`.
* Never replace `results` or `_state_lock`.