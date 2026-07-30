import { useEffect } from 'react'
import styled from 'styled-components'
import { getJson } from './api'
import { useAppStore } from './store'
import Guide from './screens/Guide'
import CostBoard from './screens/CostBoard'
import DocCheck from './screens/DocCheck'

const TABS = [
  { id: 'guide', label: '무역 길잡이' },
  { id: 'cost', label: '진짜 원가' },
  { id: 'doc', label: '서류 점검' },
]

const Header = styled.header`
  background: ${({ theme }) => theme.navy};
  color: white;
  padding: 0 28px;
`

const TitleRow = styled.div`
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 20px 0 14px;
  h1 { font-size: 21px; }
  em { color: ${({ theme }) => theme.yellow}; font-style: normal; }
  span { font-size: 13px; color: #9fb2c3; }
`

const TabRow = styled.nav`
  display: flex;
  gap: 4px;
`

const TabButton = styled.button`
  background: ${({ $active, theme }) => ($active ? theme.bgSoft : 'transparent')};
  color: ${({ $active, theme }) => ($active ? theme.navy : '#c6d2dd')};
  border: none;
  border-radius: 10px 10px 0 0;
  padding: 11px 22px;
  font-size: 15px;
  font-weight: ${({ $active }) => ($active ? 700 : 500)};
`

const Main = styled.main`
  max-width: 980px;
  margin: 24px auto 60px;
  padding: 0 20px;
`

const HealthDot = styled.span`
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  background: ${({ $ok, theme }) => ($ok ? theme.green : theme.red)};
`

export default function App() {
  const { tab, setTab, health, setHealth } = useAppStore()

  useEffect(() => {
    getJson('/health')
      .then(setHealth)
      .catch(() => setHealth({ status: 'down' }))
  }, [setHealth])

  const ok = health?.status === 'ok'
  return (
    <>
      <Header>
        <TitleRow>
          <h1>바다 건너 <em>사장님</em> ⚓</h1>
          <span>1인 수입 셀러를 위한 무역·외환 AI 에이전트</span>
          <span style={{ marginLeft: 'auto' }}>
            <HealthDot $ok={ok} />
            {health === null ? '연결 확인 중…' : ok ? 'API 연결됨' : 'API 연결 안 됨 — 백엔드를 확인하세요'}
          </span>
        </TitleRow>
        <TabRow>
          {TABS.map((t) => (
            <TabButton key={t.id} $active={tab === t.id} onClick={() => setTab(t.id)}>
              {t.label}
            </TabButton>
          ))}
        </TabRow>
      </Header>
      <Main>
        {tab === 'guide' && <Guide />}
        {tab === 'cost' && <CostBoard />}
        {tab === 'doc' && <DocCheck />}
      </Main>
    </>
  )
}
