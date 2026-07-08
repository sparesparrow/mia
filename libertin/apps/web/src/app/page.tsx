import { getDict } from '@libertin/i18n/dict';
import { CategoryCard, Hero, SiteFooter } from '@libertin/ui';

const dict = getDict('cs');

const categories = [
  { key: 'naturists', name: dict.home.categories.naturists },
  { key: 'swingers', name: dict.home.categories.swingers },
  { key: 'bdsm', name: dict.home.categories.bdsm },
  { key: 'shibari', name: dict.home.categories.shibari },
] as const;

export default function HomePage() {
  return (
    <>
      <main style={{ maxWidth: 960, margin: '0 auto', padding: '0 var(--space-6)' }}>
        <Hero
          title={dict.home.hero.title}
          subtitle={dict.home.hero.subtitle}
          ctaLabel={dict.home.hero.cta}
          ctaHref="/login"
        />

        <section aria-labelledby="categories-heading">
          <h2
            id="categories-heading"
            style={{
              textAlign: 'center',
              color: 'var(--color-text)',
              fontSize: 'var(--text-2xl)',
              fontWeight: 700,
              margin: '0 0 var(--space-6)',
            }}
          >
            {dict.home.sections.categories}
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {categories.map((category) => (
              <CategoryCard key={category.key} name={category.name} href="/login" />
            ))}
          </div>
        </section>
      </main>

      <SiteFooter
        brand={dict.meta.title}
        links={[
          { label: dict.footer.about, href: '/o-nas' },
          { label: dict.footer.contact, href: '/kontakt' },
          { label: dict.footer.privacy, href: '/soukromi' },
          { label: dict.footer.terms, href: '/podminky' },
        ]}
        ageNote={dict.footer.age}
      />
    </>
  );
}
