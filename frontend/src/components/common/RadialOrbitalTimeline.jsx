import React, { useState, useEffect, useRef } from 'react';
import { Box, Flex, Text, Badge, Button, Icon, HStack } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { FiArrowRight, FiLink, FiZap } from 'react-icons/fi';

// Adaptación a Chakra UI del componente "Radial Orbital Timeline" de 21st.dev
// (original: jatin-yadav05, TypeScript + Tailwind + shadcn/ui)

const pulseAnim = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

const pingAnim = keyframes`
  75%, 100% { transform: scale(2); opacity: 0; }
`;

const STATUS_CONFIG = {
  completed: { label: 'COMPLETADO', colorScheme: 'green' },
  'in-progress': { label: 'EN PROCESO', colorScheme: 'yellow' },
  pending: { label: 'PENDIENTE', colorScheme: 'gray' }
};

/**
 * timelineData: [{
 *   id, title, date, content, category,
 *   icon (componente react-icons), relatedIds: [ids],
 *   status: 'completed' | 'in-progress' | 'pending',
 *   energy: 0-100
 * }]
 */
const RadialOrbitalTimeline = ({
  timelineData = [],
  height = '560px',
  radius = 170,
  energyLabel = 'Avance'
}) => {
  const [expandedItems, setExpandedItems] = useState({});
  const [rotationAngle, setRotationAngle] = useState(0);
  const [autoRotate, setAutoRotate] = useState(true);
  const [pulseEffect, setPulseEffect] = useState({});
  const [activeNodeId, setActiveNodeId] = useState(null);
  const containerRef = useRef(null);
  const orbitRef = useRef(null);

  const getRelatedItems = (itemId) => {
    const currentItem = timelineData.find((item) => item.id === itemId);
    return currentItem ? currentItem.relatedIds || [] : [];
  };

  const handleContainerClick = (e) => {
    if (e.target === containerRef.current || e.target === orbitRef.current) {
      setExpandedItems({});
      setActiveNodeId(null);
      setPulseEffect({});
      setAutoRotate(true);
    }
  };

  const centerViewOnNode = (nodeId) => {
    const nodeIndex = timelineData.findIndex((item) => item.id === nodeId);
    if (nodeIndex === -1) return;
    const targetAngle = (nodeIndex / timelineData.length) * 360;
    setRotationAngle(270 - targetAngle);
  };

  const toggleItem = (id) => {
    setExpandedItems((prev) => {
      const newState = {};
      newState[id] = !prev[id];

      if (!prev[id]) {
        setActiveNodeId(id);
        setAutoRotate(false);
        const newPulse = {};
        getRelatedItems(id).forEach((relId) => {
          newPulse[relId] = true;
        });
        setPulseEffect(newPulse);
        centerViewOnNode(id);
      } else {
        setActiveNodeId(null);
        setAutoRotate(true);
        setPulseEffect({});
      }

      return newState;
    });
  };

  useEffect(() => {
    let rotationTimer;
    if (autoRotate) {
      rotationTimer = setInterval(() => {
        setRotationAngle((prev) => Number(((prev + 0.3) % 360).toFixed(3)));
      }, 50);
    }
    return () => {
      if (rotationTimer) clearInterval(rotationTimer);
    };
  }, [autoRotate]);

  const calculateNodePosition = (index, total) => {
    const angle = ((index / total) * 360 + rotationAngle) % 360;
    const radian = (angle * Math.PI) / 180;
    const x = radius * Math.cos(radian);
    const y = radius * Math.sin(radian);
    const zIndex = Math.round(100 + 50 * Math.cos(radian));
    const opacity = Math.max(0.4, Math.min(1, 0.4 + 0.6 * ((1 + Math.sin(radian)) / 2)));
    return { x, y, zIndex, opacity };
  };

  const isRelatedToActive = (itemId) => {
    if (!activeNodeId) return false;
    return getRelatedItems(activeNodeId).includes(itemId);
  };

  return (
    <Box
      ref={containerRef}
      onClick={handleContainerClick}
      w="100%"
      h={height}
      bg="gray.900"
      borderRadius="xl"
      overflow="hidden"
      position="relative"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <Box
        ref={orbitRef}
        position="absolute"
        w="100%"
        h="100%"
        display="flex"
        alignItems="center"
        justifyContent="center"
        style={{ perspective: '1000px' }}
      >
        {/* Núcleo central */}
        <Flex
          position="absolute"
          w="64px"
          h="64px"
          borderRadius="full"
          bgGradient="linear(to-br, purple.500, blue.500, teal.400)"
          animation={`${pulseAnim} 2s ease-in-out infinite`}
          align="center"
          justify="center"
          zIndex={10}
        >
          <Box
            position="absolute"
            w="80px"
            h="80px"
            borderRadius="full"
            border="1px solid"
            borderColor="whiteAlpha.300"
            animation={`${pingAnim} 1.8s cubic-bezier(0,0,0.2,1) infinite`}
          />
          <Box
            position="absolute"
            w="96px"
            h="96px"
            borderRadius="full"
            border="1px solid"
            borderColor="whiteAlpha.200"
            animation={`${pingAnim} 1.8s cubic-bezier(0,0,0.2,1) infinite`}
            sx={{ animationDelay: '0.5s' }}
          />
          <Box w="32px" h="32px" borderRadius="full" bg="whiteAlpha.800" backdropFilter="blur(8px)" />
        </Flex>

        {/* Anillo de la órbita */}
        <Box
          position="absolute"
          w={`${radius * 2}px`}
          h={`${radius * 2}px`}
          borderRadius="full"
          border="1px solid"
          borderColor="whiteAlpha.200"
        />

        {timelineData.map((item, index) => {
          const position = calculateNodePosition(index, timelineData.length);
          const isExpanded = !!expandedItems[item.id];
          const isRelated = isRelatedToActive(item.id);
          const isPulsing = !!pulseEffect[item.id];
          const ItemIcon = item.icon;
          const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
          const glowSize = (item.energy || 0) * 0.5 + 40;

          return (
            <Box
              key={item.id}
              position="absolute"
              transition="all 0.7s"
              cursor="pointer"
              style={{
                transform: `translate(${position.x}px, ${position.y}px)`,
                zIndex: isExpanded ? 200 : position.zIndex,
                opacity: isExpanded ? 1 : position.opacity
              }}
              onClick={(e) => {
                e.stopPropagation();
                toggleItem(item.id);
              }}
            >
              {/* Halo de energía */}
              <Box
                position="absolute"
                borderRadius="full"
                animation={isPulsing ? `${pulseAnim} 1s ease-in-out infinite` : undefined}
                style={{
                  background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 70%)',
                  width: `${glowSize}px`,
                  height: `${glowSize}px`,
                  left: `-${(glowSize - 40) / 2}px`,
                  top: `-${(glowSize - 40) / 2}px`
                }}
              />

              {/* Nodo */}
              <Flex
                w="40px"
                h="40px"
                borderRadius="full"
                align="center"
                justify="center"
                bg={isExpanded ? 'white' : isRelated ? 'whiteAlpha.600' : 'gray.900'}
                color={isExpanded || isRelated ? 'gray.900' : 'white'}
                border="2px solid"
                borderColor={isExpanded || isRelated ? 'white' : 'whiteAlpha.400'}
                boxShadow={isExpanded ? '0 0 20px rgba(255,255,255,0.4)' : 'none'}
                animation={isRelated && !isExpanded ? `${pulseAnim} 1.2s ease-in-out infinite` : undefined}
                transition="all 0.3s"
                transform={isExpanded ? 'scale(1.5)' : 'scale(1)'}
              >
                {ItemIcon && <Icon as={ItemIcon} boxSize={4} />}
              </Flex>

              {/* Etiqueta */}
              <Text
                position="absolute"
                top="48px"
                left="50%"
                transform={`translateX(-50%) ${isExpanded ? 'scale(1.25)' : 'scale(1)'}`}
                whiteSpace="nowrap"
                fontSize="xs"
                fontWeight="semibold"
                letterSpacing="wider"
                color={isExpanded ? 'white' : 'whiteAlpha.700'}
                transition="all 0.3s"
              >
                {item.title}
              </Text>

              {/* Tarjeta expandida */}
              {isExpanded && (
                <Box
                  position="absolute"
                  top="80px"
                  left="50%"
                  transform="translateX(-50%)"
                  w="260px"
                  bg="blackAlpha.800"
                  backdropFilter="blur(12px)"
                  border="1px solid"
                  borderColor="whiteAlpha.300"
                  borderRadius="lg"
                  boxShadow="0 0 30px rgba(255,255,255,0.1)"
                  p={4}
                  cursor="default"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Box
                    position="absolute"
                    top="-12px"
                    left="50%"
                    transform="translateX(-50%)"
                    w="1px"
                    h="12px"
                    bg="whiteAlpha.500"
                  />
                  <Flex justify="space-between" align="center" mb={2}>
                    <Badge colorScheme={statusCfg.colorScheme} fontSize="2xs" px={2}>
                      {statusCfg.label}
                    </Badge>
                    <Text fontSize="xs" fontFamily="mono" color="whiteAlpha.600">
                      {item.date}
                    </Text>
                  </Flex>
                  <Text fontSize="sm" fontWeight="bold" color="white" mb={2}>
                    {item.title}
                  </Text>
                  <Text fontSize="xs" color="whiteAlpha.800">
                    {item.content}
                  </Text>

                  <Box mt={4} pt={3} borderTop="1px solid" borderColor="whiteAlpha.200">
                    <Flex justify="space-between" align="center" fontSize="xs" mb={1}>
                      <HStack spacing={1} color="whiteAlpha.800">
                        <Icon as={FiZap} boxSize={2.5} />
                        <Text fontSize="xs">{energyLabel}</Text>
                      </HStack>
                      <Text fontSize="xs" fontFamily="mono" color="white">
                        {item.energy}%
                      </Text>
                    </Flex>
                    <Box w="100%" h="4px" bg="whiteAlpha.200" borderRadius="full" overflow="hidden">
                      <Box
                        h="100%"
                        bgGradient="linear(to-r, blue.400, purple.500)"
                        style={{ width: `${item.energy}%` }}
                      />
                    </Box>
                  </Box>

                  {(item.relatedIds || []).length > 0 && (
                    <Box mt={4} pt={3} borderTop="1px solid" borderColor="whiteAlpha.200">
                      <HStack spacing={1} mb={2} color="whiteAlpha.700">
                        <Icon as={FiLink} boxSize={2.5} />
                        <Text fontSize="2xs" textTransform="uppercase" letterSpacing="wider" fontWeight="medium">
                          Etapas conectadas
                        </Text>
                      </HStack>
                      <Flex flexWrap="wrap" gap={1}>
                        {item.relatedIds.map((relatedId) => {
                          const relatedItem = timelineData.find((i) => i.id === relatedId);
                          if (!relatedItem) return null;
                          return (
                            <Button
                              key={relatedId}
                              size="xs"
                              variant="outline"
                              h="24px"
                              px={2}
                              fontSize="xs"
                              borderColor="whiteAlpha.300"
                              color="whiteAlpha.800"
                              _hover={{ bg: 'whiteAlpha.200', color: 'white' }}
                              rightIcon={<Icon as={FiArrowRight} boxSize={2} />}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleItem(relatedId);
                              }}
                            >
                              {relatedItem.title}
                            </Button>
                          );
                        })}
                      </Flex>
                    </Box>
                  )}
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

export default RadialOrbitalTimeline;
