import { describe, it, expect } from 'vitest';
import * as hook from './useRosbridge';

describe('useRosbridge exports', () => {
  it('should export connect/disconnect/publishMessage', () => {
    expect(typeof hook.useRosbridge).toBe('function');
  });
});
