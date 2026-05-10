import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CameraPanel from './CameraPanel';
import { useAppStore } from '../store';

describe('CameraPanel', () => {
  it('renders placeholder when camera is off', () => {
    // ensure store is in default state
    const { isCameraOn } = useAppStore.getState();
    // force camera off
    useAppStore.setState({ isCameraOn: false });

    render(<CameraPanel />);
    expect(screen.getByText('摄像头已关闭')).toBeTruthy();

    // restore previous state
    useAppStore.setState({ isCameraOn });
  });
});
