import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Avatar } from './index';

describe('Avatar', () => {
  it('renders an image when a src is given', () => {
    render(<Avatar src="/u/1.jpg" alt="Profilová fotka" />);
    const img = screen.getByRole('img', { name: 'Profilová fotka' });
    expect(img).toHaveAttribute('src', '/u/1.jpg');
  });

  it('falls back to initials instead of loading a remote image', () => {
    render(<Avatar initials="LB" alt="Člen LB" />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('LB')).toBeInTheDocument();
  });

  it('renders a neutral placeholder when there are no initials', () => {
    render(<Avatar />);
    expect(screen.getByText('?')).toBeInTheDocument();
  });

  it('treats an unlabelled photo as decorative rather than exposing a filename', () => {
    render(<Avatar src="/u/discreet-photo-of-member.jpg" />);
    const img = screen.getByRole('presentation', { hidden: true });
    expect(img).toHaveAttribute('alt', '');
  });

  it('scales to the requested size', () => {
    const { rerender } = render(<Avatar initials="AA" alt="a" />);
    expect(screen.getByText('AA')).toHaveStyle({ width: '48px', height: '48px' });
    rerender(<Avatar initials="AA" alt="a" size="lg" />);
    expect(screen.getByText('AA')).toHaveStyle({ width: '80px', height: '80px' });
  });
});
