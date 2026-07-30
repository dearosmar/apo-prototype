import styled, { keyframes } from 'styled-components'

export const Card = styled.div`
  background: ${({ theme }) => theme.bg};
  border-radius: ${({ theme }) => theme.radius};
  box-shadow: ${({ theme }) => theme.shadow};
  padding: 20px;
`

export const PrimaryButton = styled.button`
  background: ${({ theme }) => theme.yellow};
  color: ${({ theme }) => theme.navy};
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 700;
  font-size: 15px;
  &:disabled { opacity: 0.5; cursor: default; }
`

export const GhostButton = styled.button`
  background: ${({ theme }) => theme.bg};
  color: ${({ theme }) => theme.navy};
  border: 1px solid #d7dee5;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 13px;
  &:hover { border-color: ${({ theme }) => theme.yellow}; }
`

export const ErrorBox = styled.div`
  background: #fdf0f0;
  color: ${({ theme }) => theme.red};
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
`

export const NoticeBox = styled.div`
  background: #fff8e6;
  color: #7a5b00;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
`

const pulse = keyframes`
  0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; }
`

export const Skeleton = styled.div`
  height: ${({ h }) => h || '16px'};
  width: ${({ w }) => w || '100%'};
  border-radius: 6px;
  background: #e4e9ee;
  animation: ${pulse} 1.2s ease-in-out infinite;
`

export const SectionTitle = styled.h3`
  color: ${({ theme }) => theme.navy};
  font-size: 16px;
  margin-bottom: 12px;
`
