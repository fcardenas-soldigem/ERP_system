import React, { useCallback, useRef, useState } from 'react';
import {
  Box, Icon, Text, VStack, HStack, Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiUploadCloud, FiFile, FiX } from 'react-icons/fi';

const ACCEPTED = ['.xlsx', '.xls', '.csv'];
const MAX_MB   = 20;

export default function DropZone({ onFile, disabled }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile]         = useState(null);
  const [error, setError]       = useState('');
  const inputRef                = useRef(null);

  const borderColor   = useColorModeValue('gray.300', 'gray.600');
  const hoverBg       = useColorModeValue('blue.50', 'blue.900');
  const dragBg        = useColorModeValue('blue.100', 'blue.800');
  const textColor     = useColorModeValue('gray.500', 'gray.400');
  const fileBg        = useColorModeValue('gray.50', 'gray.700');

  const validate = (f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      return `Formato no soportado. Use ${ACCEPTED.join(', ')}`;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      return `El archivo supera los ${MAX_MB} MB`;
    }
    return null;
  };

  const handleFile = useCallback((f) => {
    const err = validate(f);
    if (err) { setError(err); return; }
    setError('');
    setFile(f);
    onFile(f);
  }, [onFile]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [disabled, handleFile]);

  const onDragOver = (e) => { e.preventDefault(); if (!disabled) setDragging(true); };
  const onDragLeave = () => setDragging(false);

  const onInputChange = (e) => {
    const f = e.target.files[0];
    if (f) handleFile(f);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    setFile(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <VStack spacing={3} w="full">
      <Box
        w="full"
        minH="180px"
        border="2px dashed"
        borderColor={dragging ? 'blue.400' : error ? 'red.400' : borderColor}
        borderRadius="xl"
        bg={dragging ? dragBg : 'transparent'}
        cursor={disabled ? 'not-allowed' : 'pointer'}
        transition="all 0.2s"
        _hover={!disabled ? { bg: hoverBg, borderColor: 'blue.400' } : {}}
        display="flex"
        alignItems="center"
        justifyContent="center"
        onClick={() => !disabled && inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        opacity={disabled ? 0.6 : 1}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          onChange={onInputChange}
          style={{ display: 'none' }}
          disabled={disabled}
        />
        {file ? (
          <HStack spacing={3} px={6} py={4}>
            <Icon as={FiFile} boxSize={7} color="blue.500" />
            <VStack align="start" spacing={0}>
              <Text fontWeight="semibold" fontSize="sm">{file.name}</Text>
              <Text fontSize="xs" color={textColor}>
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </Text>
            </VStack>
            <Icon
              as={FiX}
              boxSize={4}
              color="gray.400"
              cursor="pointer"
              _hover={{ color: 'red.400' }}
              onClick={clearFile}
            />
          </HStack>
        ) : (
          <VStack spacing={2} py={8} px={6}>
            <Icon
              as={FiUploadCloud}
              boxSize={10}
              color={dragging ? 'blue.500' : 'gray.400'}
            />
            <Text fontSize="sm" fontWeight="medium" color={textColor}>
              Arrastra tu archivo aquí o{' '}
              <Text as="span" color="blue.500" fontWeight="semibold">
                selecciónalo
              </Text>
            </Text>
            <HStack spacing={2}>
              {ACCEPTED.map(ext => (
                <Badge key={ext} variant="subtle" colorScheme="gray" fontSize="10px">
                  {ext}
                </Badge>
              ))}
            </HStack>
            <Text fontSize="11px" color={textColor}>Máximo {MAX_MB} MB</Text>
          </VStack>
        )}
      </Box>

      {error && (
        <Text fontSize="sm" color="red.500" alignSelf="start">
          {error}
        </Text>
      )}
    </VStack>
  );
}
