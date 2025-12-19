import React from 'react';
import { Box } from '@chakra-ui/react';
import { motion } from 'framer-motion';

export const AuroraBackground = ({ children, showRadialGradient = true, ...props }) => {
  return (
    <Box
      position="relative"
      display="flex"
      flexDirection="column"
      minH="100vh"
      w="100%"
      alignItems="center"
      justifyContent="flex-start"
      bg="white"
      overflow="hidden"
      {...props}
    >
      {/* Aurora Effect */}
      <Box
        position="absolute"
        inset="0"
        overflow="hidden"
        pointerEvents="none"
      >
        <Box
          position="absolute"
          inset="-10px"
          opacity="0.5"
          filter="blur(10px)"
          sx={{
            background: `
              repeating-linear-gradient(
                100deg,
                rgba(255, 255, 255, 0.8) 0%,
                rgba(255, 255, 255, 0.8) 7%,
                transparent 10%,
                transparent 12%,
                rgba(255, 255, 255, 0.8) 16%
              ),
              repeating-linear-gradient(
                100deg,
                #3b82f6 10%,
                #818cf8 15%,
                #93c5fd 20%,
                #ddd6fe 25%,
                #60a5fa 30%
              )
            `,
            backgroundSize: '300%, 200%',
            backgroundPosition: '50% 50%, 50% 50%',
            animation: 'aurora 60s linear infinite',
            '@keyframes aurora': {
              from: {
                backgroundPosition: '50% 50%, 50% 50%',
              },
              to: {
                backgroundPosition: '350% 50%, 350% 50%',
              },
            },
            _dark: {
              background: `
                repeating-linear-gradient(
                  100deg,
                  rgba(0, 0, 0, 0.8) 0%,
                  rgba(0, 0, 0, 0.8) 7%,
                  transparent 10%,
                  transparent 12%,
                  rgba(0, 0, 0, 0.8) 16%
                ),
                repeating-linear-gradient(
                  100deg,
                  #3b82f6 10%,
                  #818cf8 15%,
                  #93c5fd 20%,
                  #ddd6fe 25%,
                  #60a5fa 30%
                )
              `,
            },
            ...(showRadialGradient && {
              maskImage: 'radial-gradient(ellipse at 100% 0%, black 10%, transparent 70%)',
            }),
          }}
        />
      </Box>

      {/* Content */}
      <Box
        position="relative"
        zIndex="1"
        w="100%"
        display="flex"
        flexDirection="column"
        alignItems="stretch"
      >
        {children}
      </Box>
    </Box>
  );
};

