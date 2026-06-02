import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Box, Flex, SimpleGrid } from '@chakra-ui/react';
import StatCard from './StatCard';

/**
 * Desktop (sm+): 4-column grid, all cards visible simultaneously.
 * Mobile (base):  horizontal scroll carousel with snap + dot indicators.
 *
 * F-003 fix: removed invalid `columns={{ base: 0 }}` — display handles visibility.
 * F-004 fix: dot index computed from IntersectionObserver, not scrollWidth math.
 */
const StatCardsCarousel = ({ cards = [] }) => {
  const scrollRef  = useRef(null);
  const cardRefs   = useRef([]);
  const [activeIdx, setActiveIdx] = useState(0);

  // ── Observe which card is most visible (F-004: replaces scrollWidth math) ──
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let maxRatio = 0;
        let mostVisible = activeIdx;
        entries.forEach((entry) => {
          const idx = Number(entry.target.dataset.idx);
          if (entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            mostVisible = idx;
          }
        });
        if (maxRatio > 0) setActiveIdx(mostVisible);
      },
      {
        root: container,
        threshold: [0.4, 0.6, 0.8],
      }
    );

    cardRefs.current.forEach((el) => { if (el) observer.observe(el); });
    return () => observer.disconnect();
  }, [cards.length]);

  // ── Navigate to card by index ─────────────────────────────────────────────
  const scrollTo = useCallback((idx) => {
    const el = cardRefs.current[idx];
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
  }, []);

  return (
    <Box>
      {/* ── Desktop: standard 4-column grid ── */}
      <SimpleGrid
        columns={{ sm: 2, lg: 4 }}
        spacing={4}
        display={{ base: 'none', sm: 'grid' }}
      >
        {cards.map((c, i) => <StatCard key={i} {...c} />)}
      </SimpleGrid>

      {/* ── Mobile: scroll-snap carousel ── */}
      <Box display={{ base: 'block', sm: 'none' }}>
        <Flex
          ref={scrollRef}
          gap={3}
          overflowX="auto"
          pb={1}
          // Prevent translateY hover from clipping inside this container
          sx={{
            scrollSnapType: 'x mandatory',
            scrollBehavior: 'smooth',
            '&::-webkit-scrollbar': { display: 'none' },
            msOverflowStyle: 'none',
            scrollbarWidth: 'none',
            // Clip overflow so card hover shadow stays contained
            overflowY: 'visible',
          }}
        >
          {cards.map((c, i) => (
            <Box
              key={i}
              ref={(el) => { cardRefs.current[i] = el; }}
              data-idx={i}
              flexShrink={0}
              // 80vw → single card centered with visible hint of next
              w="80vw"
              maxW="320px"
              scrollSnapAlign="start"
            >
              <StatCard {...c} />
            </Box>
          ))}
          {/* Trailing spacer ensures last card can fully snap into view */}
          <Box flexShrink={0} minW="4px" />
        </Flex>

        {/* Dot indicators — pill shape for active, circle for inactive */}
        <Flex justify="center" gap={1.5} mt={3}>
          {cards.map((_, i) => (
            <Box
              key={i}
              as="button"
              type="button"
              w={i === activeIdx ? '16px' : '6px'}
              h="6px"
              borderRadius="full"
              bg={i === activeIdx ? 'blue.500' : 'gray.200'}
              transition="all 0.25s ease"
              cursor="pointer"
              onClick={() => scrollTo(i)}
              aria-label={`Ir a card ${i + 1}`}
            />
          ))}
        </Flex>
      </Box>
    </Box>
  );
};

export default StatCardsCarousel;
