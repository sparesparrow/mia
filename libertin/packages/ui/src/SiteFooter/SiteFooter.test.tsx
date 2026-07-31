import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SiteFooter } from './index';

const links = [
  { label: 'Podmínky', href: '/podminky' },
  { label: 'Soukromí', href: '/soukromi' },
];

describe('SiteFooter', () => {
  it('renders every link with its href', () => {
    render(<SiteFooter brand="Libertin" links={links} ageNote="Pouze 18+" />);
    expect(screen.getByRole('link', { name: 'Podmínky' })).toHaveAttribute('href', '/podminky');
    expect(screen.getByRole('link', { name: 'Soukromí' })).toHaveAttribute('href', '/soukromi');
  });

  it('exposes the links inside a labelled navigation landmark', () => {
    render(<SiteFooter brand="Libertin" links={links} ageNote="Pouze 18+" />);
    const nav = screen.getByRole('navigation', { name: 'Libertin' });
    expect(nav.querySelectorAll('a')).toHaveLength(2);
  });

  it('always shows the age note (a legal requirement for the public site)', () => {
    render(<SiteFooter brand="Libertin" links={links} ageNote="Obsah pouze pro 18+" />);
    expect(screen.getByText('Obsah pouze pro 18+')).toBeInTheDocument();
  });

  it('renders an empty list without crashing', () => {
    render(<SiteFooter brand="Libertin" links={[]} ageNote="Pouze 18+" />);
    expect(screen.queryAllByRole('link')).toHaveLength(0);
  });
});
