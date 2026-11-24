import test from 'node:test';
import assert from 'node:assert/strict';
import { BELL_DURATION_SECONDS, createBellVoice, tryRingBell } from '../web/bell.mjs';

class MockAudioParam {
  value = 1;
  events = [];

  setValueAtTime(value, time) {
    this.events.push({ type: 'set', value, time });
    this.value = value;
    return this;
  }

  linearRampToValueAtTime(value, time) {
    this.events.push({ type: 'linear', value, time });
    return this;
  }

  exponentialRampToValueAtTime(value, time) {
    assert.ok(value > 0);
    this.events.push({ type: 'exponential', value, time });
    return this;
  }

  cancelScheduledValues(time) {
    this.events.push({ type: 'cancel', time });
    return this;
  }
}

class MockNode {
  connections = [];
  disconnectCalls = 0;

  connect(node) {
    this.connections.push(node);
    return node;
  }

  disconnect() {
    this.disconnectCalls++;
    this.connections = [];
  }
}

function makeHarness(initialState = 'running') {
  const contexts = [];
  const timers = new Map();
  const clearedTimers = [];
  let nextTimerId = 0;

  class MockContext {
    state = initialState;
    currentTime = 8;
    destination = {};
    gains = [];
    oscillators = [];
    listeners = new Set();
    closeCalls = 0;
    resumeCalls = 0;

    constructor() {
      contexts.push(this);
    }

    createGain() {
      const node = new MockNode();
      node.gain = new MockAudioParam();
      this.gains.push(node);
      return node;
    }

    createOscillator() {
      const node = new MockNode();
      node.frequency = new MockAudioParam();
      node.starts = [];
      node.stops = [];
      node.start = (time) => node.starts.push(time);
      node.stop = (time) => node.stops.push(time);
      this.oscillators.push(node);
      return node;
    }

    addEventListener(type, listener) {
      assert.equal(type, 'statechange', 'only playback-state observation is allowed');
      this.listeners.add(listener);
    }

    removeEventListener(type, listener) {
      assert.equal(type, 'statechange');
      this.listeners.delete(listener);
    }

    changeState(state) {
      this.state = state;
      for (const listener of [...this.listeners]) listener();
    }

    close() {
      this.closeCalls++;
      this.changeState('closed');
      return Promise.resolve();
    }

    resume() {
      this.resumeCalls++;
      throw new Error('Audio must never be resumed.');
    }
  }

  const options = {
    AudioContextClass: MockContext,
    setTimeoutFn(callback, delay) {
      assert.ok(Number.isFinite(delay) && delay >= 0);
      const id = nextTimerId++;
      timers.set(id, { callback, delay });
      return id;
    },
    clearTimeoutFn(id) {
      clearedTimers.push(id);
      timers.delete(id);
    },
  };

  return {
    options, contexts, timers, clearedTimers,
    get context() { return contexts[0]; },
    fireTimer() {
      assert.equal(timers.size, 1);
      const [id, { callback }] = [...timers][0];
      timers.delete(id);
      callback();
    },
  };
}

test('missing audio support returns an idempotent silent handle without timers', () => {
  const harness = makeHarness();
  const bell = tryRingBell({ ...harness.options, AudioContextClass: null });
  assert.equal(bell.status, 'unavailable');
  bell.stop();
  bell.stop();
  assert.equal(harness.contexts.length, 0);
  assert.equal(harness.timers.size, 0);
});

test('default constructor lookup supports standard, prefixed and absent global APIs', (t) => {
  const keys = ['AudioContext', 'webkitAudioContext'];
  const original = keys.map((key) => Object.getOwnPropertyDescriptor(globalThis, key));
  t.after(() => {
    keys.forEach((key, index) => {
      if (original[index]) Object.defineProperty(globalThis, key, original[index]);
      else delete globalThis[key];
    });
  });

  for (const key of keys) {
    for (const name of keys) {
      Object.defineProperty(globalThis, name, { configurable: true, value: undefined });
    }
    const harness = makeHarness();
    Object.defineProperty(globalThis, key, { configurable: true, value: harness.options.AudioContextClass });
    const { setTimeoutFn, clearTimeoutFn } = harness.options;
    const bell = tryRingBell({ setTimeoutFn, clearTimeoutFn });
    assert.equal(bell.status, 'started', key);
    harness.fireTimer();
    assert.equal(harness.context.closeCalls, 1);
  }

  for (const name of keys) {
    Object.defineProperty(globalThis, name, { configurable: true, value: undefined });
  }
  assert.equal(tryRingBell().status, 'unavailable');
});

for (const state of ['suspended', 'interrupted', 'closed']) {
  test(`initial ${state} context stays silent without oscillators, timers or resume`, () => {
    const harness = makeHarness(state);
    const bell = tryRingBell(harness.options);
    const context = harness.context;
    assert.equal(bell.status, 'blocked');
    assert.equal(context.closeCalls, state === 'closed' ? 0 : 1);
    assert.equal(context.gains.length, 0);
    assert.equal(context.oscillators.length, 0);
    assert.equal(context.resumeCalls, 0);
    assert.equal(context.listeners.size, 0);
    assert.equal(harness.timers.size, 0);
    bell.stop();
    bell.stop();
    context.changeState('running');
    assert.equal(context.oscillators.length, 0);
    assert.equal(harness.timers.size, 0);
  });
}

test('known DOM constructor permission and support errors are classified and logged', (t) => {
  const warnings = [];
  t.mock.method(console, 'warn', (...args) => warnings.push(args));
  for (const [name, status] of [
    ['NotAllowedError', 'blocked'], ['SecurityError', 'blocked'], ['NotSupportedError', 'unavailable'],
  ]) {
    const error = new DOMException('Platform refused audio.', name);
    const bell = tryRingBell({
      AudioContextClass: class { constructor() { throw error; } },
    });
    assert.equal(bell.status, status);
    bell.stop();
    assert.equal(warnings.at(-1)[1], error);
  }
  assert.equal(warnings.length, 3);
});

test('unknown constructor errors propagate unchanged to the caller', (t) => {
  const warnings = [];
  t.mock.method(console, 'warn', (...args) => warnings.push(args));
  const misleadingName = new Error('Not a platform exception.');
  misleadingName.name = 'NotAllowedError';
  for (const error of [
    new TypeError('Broken integration.'), new Error('Unexpected failure.'),
    new DOMException('Unknown DOM failure.', 'InvalidStateError'), misleadingName,
    new DOMException('Unknown inherited name.', 'toString'),
    new DOMException('Unknown inherited name.', '__proto__'),
  ]) {
    assert.throws(() => tryRingBell({
      AudioContextClass: class { constructor() { throw error; } },
    }), (actual) => actual === error);
  }
  assert.throws(() => tryRingBell({ AudioContextClass: {} }), TypeError);
  assert.equal(warnings.length, 0);
});

test('voice scheduling supports suspended offline contexts and bounds the complete bell', () => {
  const harness = makeHarness('suspended');
  const context = new harness.options.AudioContextClass();
  const { endTime, output } = createBellVoice(context);
  const now = context.currentTime;
  assert.ok(BELL_DURATION_SECONDS >= 1 && BELL_DURATION_SECONDS <= 1.4);
  assert.equal(endTime, now + BELL_DURATION_SECONDS);
  assert.equal(output, context.gains[0]);
  assert.deepEqual(output.connections, [context.destination]);
  assert.equal(context.oscillators.length, 4);
  assert.equal(context.gains.length, 5);

  let sumOfPeakWeights = 0;
  const frequencies = [];
  for (const [index, oscillator] of context.oscillators.entries()) {
    const envelope = context.gains[index + 1];
    assert.equal(oscillator.type, 'sine');
    assert.deepEqual(oscillator.connections, [envelope]);
    assert.deepEqual(envelope.connections, [output]);
    assert.equal(oscillator.starts.length, 1);
    assert.equal(oscillator.stops.length, 1);
    assert.ok(oscillator.starts[0] >= now);
    assert.ok(oscillator.stops[0] > oscillator.starts[0] && oscillator.stops[0] <= endTime);
    const events = envelope.gain.events;
    assert.deepEqual(events.map((event) => event.type), ['set', 'linear', 'exponential', 'linear']);
    assert.equal(events[0].value, 0);
    assert.equal(events[0].time, oscillator.starts[0]);
    assert.ok(events[1].time - events[0].time >= 0.01, 'attack is gentle rather than a step');
    assert.ok(events[1].time - events[0].time <= 0.04);
    assert.ok(events[2].value < events[1].value * 0.01);
    assert.equal(events[3].value, 0);
    assert.equal(events[3].time, oscillator.stops[0]);
    for (const [eventIndex, event] of events.entries()) {
      assert.ok(event.time >= now && event.time <= endTime);
      assert.ok(event.value >= 0 && event.value <= 1);
      if (eventIndex > 0) assert.ok(event.time > events[eventIndex - 1].time);
    }
    sumOfPeakWeights += events[1].value;
    frequencies.push(oscillator.frequency.events[0].value);
  }

  const masterPeak = output.gain.events[0].value;
  assert.ok(masterPeak > 0 && masterPeak * sumOfPeakWeights <= 0.15);
  assert.equal(Math.max(...context.oscillators.flatMap((node) => node.stops)), endTime);
  assert.ok(frequencies.every((frequency) => frequency >= 500 && frequency <= 4000));
  assert.ok(frequencies.some((frequency) => frequency / frequencies[0] % 1 > 0.1), 'partials are inharmonic');
  assert.equal(context.closeCalls, 0, 'the renderer owns its supplied context');
  assert.equal(context.resumeCalls, 0);
  assert.equal(context.listeners.size, 0);
  assert.equal(harness.timers.size, 0);
});

test('a running bell has one bounded completion timer and releases its context', () => {
  const harness = makeHarness();
  const bell = tryRingBell(harness.options);
  const context = harness.context;
  const output = context.gains[0];
  assert.equal(bell.status, 'started');
  assert.equal(context.oscillators.length, 4);
  assert.equal(context.closeCalls, 0);
  assert.equal(context.listeners.size, 1);
  assert.equal(harness.timers.size, 1);
  const { delay } = [...harness.timers.values()][0];
  assert.ok(delay >= BELL_DURATION_SECONDS * 1000);
  assert.ok(delay <= BELL_DURATION_SECONDS * 1000 + 50);
  harness.fireTimer();
  assert.equal(context.closeCalls, 1);
  assert.equal(context.state, 'closed');
  assert.equal(context.resumeCalls, 0);
  assert.equal(context.listeners.size, 0);
  assert.equal(output.disconnectCalls, 1);
  assert.deepEqual(output.connections, []);
  assert.equal(harness.timers.size, 0);
  bell.stop();
  bell.stop();
  assert.equal(context.closeCalls, 1);
});

test('repeated skip fades once, replaces even a zero-ID timer, and closes promptly', () => {
  const harness = makeHarness();
  const bell = tryRingBell(harness.options);
  const context = harness.context;
  const output = context.gains[0];
  context.currentTime += 0.2;
  bell.stop();
  bell.stop();
  assert.deepEqual(harness.clearedTimers, [0]);
  assert.equal(harness.timers.size, 1);
  assert.equal(context.closeCalls, 0, 'allow the short fade before release');
  const events = output.gain.events.slice(1);
  assert.deepEqual(events.map((event) => event.type), ['cancel', 'set', 'linear']);
  assert.equal(events[0].time, context.currentTime);
  assert.equal(events[1].time, context.currentTime);
  assert.equal(events[1].value, output.gain.events[0].value);
  assert.equal(events[2].value, 0);
  assert.ok(events[2].time > context.currentTime && events[2].time <= context.currentTime + 0.05);
  const { delay } = [...harness.timers.values()][0];
  assert.ok(delay >= 30 && delay <= 60);
  harness.fireTimer();
  bell.stop();
  assert.equal(context.closeCalls, 1);
  assert.equal(output.disconnectCalls, 1);
  assert.equal(context.listeners.size, 0);
  assert.equal(context.resumeCalls, 0);
  assert.equal(harness.timers.size, 0);
});

for (const state of ['suspended', 'interrupted']) {
  test(`later ${state} immediately disconnects, clears timers and cannot replay`, () => {
    const harness = makeHarness();
    const bell = tryRingBell(harness.options);
    const context = harness.context;
    const output = context.gains[0];
    context.changeState(state);
    assert.equal(output.disconnectCalls, 1);
    assert.equal(context.closeCalls, 1);
    assert.equal(context.listeners.size, 0);
    assert.equal(harness.timers.size, 0);
    bell.stop();
    context.changeState('running');
    assert.equal(context.oscillators.length, 4);
    assert.deepEqual(output.connections, []);
    assert.equal(context.resumeCalls, 0);
    assert.equal(context.closeCalls, 1);
    assert.equal(harness.timers.size, 0);
  });
}

test('suspension during a skip fade releases immediately instead of leaving a delayed timer', () => {
  const harness = makeHarness();
  const bell = tryRingBell(harness.options);
  bell.stop();
  harness.context.changeState('suspended');
  assert.equal(harness.timers.size, 0);
  assert.equal(harness.context.closeCalls, 1);
  bell.stop();
  assert.equal(harness.context.closeCalls, 1);
});

test('stop detects suspension without waiting for a statechange event', () => {
  const harness = makeHarness();
  const bell = tryRingBell(harness.options);
  harness.context.state = 'suspended';
  bell.stop();
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.gains[0].gain.events.length, 1, 'no suspended fade is queued');
  assert.equal(harness.timers.size, 0);
});

test('external context closure clears resources without closing a second time', () => {
  const harness = makeHarness();
  const bell = tryRingBell(harness.options);
  harness.context.changeState('closed');
  bell.stop();
  assert.equal(harness.context.closeCalls, 0);
  assert.equal(harness.context.listeners.size, 0);
  assert.equal(harness.context.gains[0].disconnectCalls, 1);
  assert.equal(harness.timers.size, 0);
});

test('unknown voice setup failures close the context and propagate unchanged', (t) => {
  const harness = makeHarness();
  const error = new TypeError('Broken oscillator setup.');
  t.mock.method(harness.options.AudioContextClass.prototype, 'createOscillator', () => { throw error; });
  assert.throws(() => tryRingBell(harness.options), (actual) => actual === error);
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.listeners.size, 0);
  assert.equal(harness.timers.size, 0);
  assert.deepEqual(harness.context.gains[0].connections, [], 'a partial graph was never audible');
});

test('completion timer setup failures release the voice and propagate unchanged', () => {
  const harness = makeHarness();
  const error = new TypeError('Broken timer.');
  assert.throws(() => tryRingBell({
    ...harness.options, setTimeoutFn() { throw error; },
  }), (actual) => actual === error);
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.gains[0].disconnectCalls, 1);
  assert.equal(harness.context.listeners.size, 0);
  assert.equal(harness.timers.size, 0);
});

test('failed fade automation is logged and still releases immediately', (t) => {
  const harness = makeHarness();
  const errors = [];
  const error = new Error('Cannot automate gain.');
  t.mock.method(console, 'error', (...args) => errors.push(args));
  const bell = tryRingBell(harness.options);
  t.mock.method(harness.context.gains[0].gain, 'cancelScheduledValues', () => { throw error; });
  bell.stop();
  bell.stop();
  assert.equal(errors.length, 1);
  assert.equal(errors[0][1], error);
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.gains[0].disconnectCalls, 1);
  assert.equal(harness.timers.size, 0);
});

test('disconnect failures are logged without preventing context close', (t) => {
  const harness = makeHarness();
  const errors = [];
  const error = new Error('Disconnect failed.');
  t.mock.method(console, 'error', (...args) => errors.push(args));
  const bell = tryRingBell(harness.options);
  t.mock.method(harness.context.gains[0], 'disconnect', () => { throw error; });
  harness.fireTimer();
  bell.stop();
  assert.equal(errors.length, 1);
  assert.equal(errors[0][1], error);
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.listeners.size, 0);
  assert.equal(harness.timers.size, 0);
});

for (const asynchronous of [false, true]) {
  test(`${asynchronous ? 'rejected' : 'thrown'} close failures are logged without retries or pending audio`, async (t) => {
    const harness = makeHarness('suspended');
    const errors = [];
    const error = new Error('Close failed.');
    t.mock.method(console, 'error', (...args) => errors.push(args));
    t.mock.method(harness.options.AudioContextClass.prototype, 'close', function () {
      this.closeCalls++;
      if (asynchronous) return Promise.reject(error);
      throw error;
    });
    const bell = tryRingBell(harness.options);
    await Promise.resolve();
    bell.stop();
    bell.stop();
    assert.equal(bell.status, 'blocked');
    assert.equal(errors.length, 1);
    assert.equal(errors[0][1], error);
    assert.equal(harness.context.closeCalls, 1);
    assert.equal(harness.context.oscillators.length, 0);
    assert.equal(harness.context.resumeCalls, 0);
    assert.equal(harness.timers.size, 0);
  });
}

test('later suspension disconnects scheduled sound even if context close rejects', async (t) => {
  const harness = makeHarness();
  const errors = [];
  const error = new Error('Close rejected.');
  t.mock.method(console, 'error', (...args) => errors.push(args));
  const bell = tryRingBell(harness.options);
  t.mock.method(harness.context, 'close', function () {
    this.closeCalls++;
    return Promise.reject(error);
  });
  harness.context.changeState('suspended');
  await Promise.resolve();
  bell.stop();
  harness.context.changeState('running');
  assert.equal(errors.length, 1);
  assert.equal(errors[0][1], error);
  assert.deepEqual(harness.context.gains[0].connections, []);
  assert.equal(harness.context.closeCalls, 1);
  assert.equal(harness.context.listeners.size, 0);
  assert.equal(harness.timers.size, 0);
});
