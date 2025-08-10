import React, { useState } from 'react';
import { Box, VStack, Icon, Text, Flex, useColorModeValue, Collapse, Button } from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import {
  FiHome,
  FiShoppingCart,
  FiShoppingBag,
  FiPackage,
  FiUsers,
  FiSettings,
} from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';

const MenuItem = ({ icon, children, to, subItems, isOpen, onToggle }) => {
  const activeBg = useColorModeValue('gray.100', 'gray.700');
  const hoverBg = useColorModeValue('gray.50', 'gray.600');

  if (subItems) {
    return (
      <Box width="100%">
        <Flex
          align="center"
          p="4"
          mx="4"
          borderRadius="lg"
          role="group"
          cursor="pointer"
          onClick={onToggle}
          _hover={{
            bg: hoverBg,
          }}
        >
          <Icon
            mr="4"
            fontSize="16"
            as={icon}
          />
          <Text flex="1">{children}</Text>
          <Icon
            as={isOpen ? ChevronUpIcon : ChevronDownIcon}
            transition="all .25s ease-in-out"
          />
        </Flex>
        <Collapse in={isOpen}>
          <VStack pl={8} mt={1} spacing={1}>
            {subItems.map((item, index) => (
              <NavLink
                key={index}
                to={item.path}
                style={({ isActive }) => ({
                  backgroundColor: isActive ? activeBg : 'transparent',
                  textDecoration: 'none',
                  width: '100%',
                  borderRadius: '8px',
                })}
              >
                <Flex
                  align="center"
                  p="3"
                  mx="4"
                  borderRadius="lg"
                  role="group"
                  cursor="pointer"
                  _hover={{
                    bg: hoverBg,
                  }}
                >
                  <Text>{item.name}</Text>
                </Flex>
              </NavLink>
            ))}
          </VStack>
        </Collapse>
      </Box>
    );
  }

  return (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        backgroundColor: isActive ? activeBg : 'transparent',
        textDecoration: 'none',
        width: '100%',
        borderRadius: '8px',
      })}
    >
      <Flex
        align="center"
        p="4"
        mx="4"
        borderRadius="lg"
        role="group"
        cursor="pointer"
        _hover={{
          bg: hoverBg,
        }}
      >
        <Icon
          mr="4"
          fontSize="16"
          as={icon}
        />
        <Text>{children}</Text>
      </Flex>
    </NavLink>
  );
};

const Sidebar = ({ menuItems }) => {
  const [openMenus, setOpenMenus] = useState({});

  const toggleMenu = (menuName) => {
    setOpenMenus(prev => ({
      ...prev,
      [menuName]: !prev[menuName]
    }));
  };

  return (
    <Box
      w="240px"
      h="100vh"
      borderRight="1px"
      borderRightColor={useColorModeValue('gray.200', 'gray.700')}
      py={5}
    >
      <VStack spacing={1} align="stretch">
        {menuItems.map((item, index) => (
          <MenuItem
            key={index}
            icon={item.icon}
            to={item.path}
            subItems={item.subItems}
            isOpen={openMenus[item.name]}
            onToggle={() => toggleMenu(item.name)}
          >
            {item.name}
          </MenuItem>
        ))}
      </VStack>
    </Box>
  );
};

export default Sidebar; 