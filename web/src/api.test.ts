import { describe, expect, it } from 'vite-plus/test';
import { parseLines } from './api';

describe('parseLines', () => {
  it('returns complete events and keeps the partial line', () => {
    const { events, rest } = parseLines('{"type":"delta","text":"おか"}\n{"type":"delta","te');
    expect(events).toEqual([{ type: 'delta', text: 'おか' }]);
    expect(rest).toBe('{"type":"delta","te');
  });

  it('handles several events and blank lines', () => {
    const { events, rest } = parseLines('{"type":"delta","text":"a"}\n\n{"type":"done"}\n');
    expect(events).toEqual([{ type: 'delta', text: 'a' }, { type: 'done' }]);
    expect(rest).toBe('');
  });
});
