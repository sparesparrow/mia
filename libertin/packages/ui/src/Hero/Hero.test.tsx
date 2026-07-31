import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Hero } from './index';
import { CategoryCard } from '../CategoryCard';
import { Card } from '../Card';

describe('Hero', () => {
  it('renders the title as the page-level heading and links the CTA', () => {
    render(
      <Hero title="Libertin" subtitle="Diskrétní síť" ctaLabel="Vstoupit" ctaHref="/registrace" />,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Libertin' })).toBeInTheDocument();
    expect(screen.getByText('Diskrétní síť')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Vstoupit' })).toHaveAttribute('href', '/registrace');
  });

  it('renders in a section landmark styled from tokens only', () => {
    const { container } = render(
      <Hero title="Libertin" subtitle="s" ctaLabel="c" ctaHref="#" />,
    );
    const section = container.querySelector('section');
    expect(section).not.toBeNull();
    expect(section?.getAttribute('style') ?? '').not.toMatch(/#[0-9a-f]{3,8}/i);
  });
});

describe('CategoryCard', () => {
  it('links to the category and shows its name', () => {
    render(<CategoryCard name="Shibari" href="/kategorie/shibari" />);
    const link = screen.getByRole('link', { name: 'Shibari' });
    expect(link).toHaveAttribute('href', '/kategorie/shibari');
  });

  it('hides the decorative initial from assistive tech so the name is read once', () => {
    render(<CategoryCard name="Shibari" href="/kategorie/shibari" />);
    // The accessible name must not become "S Shibari".
    expect(screen.getByRole('link', { name: 'Shibari' })).toBeInTheDocument();
    expect(screen.getByText('S')).toHaveAttribute('aria-hidden');
  });
});

describe('Card', () => {
  it('renders its children inside a div by default', () => {
    const { container } = render(<Card>obsah</Card>);
    expect(container.firstElementChild?.tagName).toBe('DIV');
    expect(screen.getByText('obsah')).toBeInTheDocument();
  });

  it('renders as the requested element when `as` is given', () => {
    const { container } = render(<Card as="article">obsah</Card>);
    expect(container.firstElementChild?.tagName).toBe('ARTICLE');
  });

  it('merges caller styles over the token base', () => {
    const { container } = render(<Card style={{ padding: 0 }}>obsah</Card>);
    const style = container.firstElementChild?.getAttribute('style') ?? '';
    expect(style).toContain('var(--color-surface)');
    expect(style).toContain('padding: 0');
  });
});
