import { useRef, useState } from 'react'
import styled from 'styled-components'
import { postFile, postJson } from '../api'
import { useAppStore } from '../store'
import { Card, GhostButton, ErrorBox, NoticeBox, Skeleton, SectionTitle } from '../components/common'

const STATUS = {
  green: { icon: '🟢', label: '안전', color: '#1B9E4B' },
  yellow: { icon: '🟡', label: '주의', color: '#E8A400' },
  red: { icon: '🔴', label: '위험', color: '#D64545' },
}

const FIELD_LABELS = [
  ['payment_terms', '결제조건'],
  ['deposit_pct', '선금 비율(%)'],
  ['incoterms', '인코텀즈'],
  ['lead_time_days', '납기(일)'],
  ['quantity', '수량'],
  ['unit_price', '단가'],
  ['total_amount', '총액'],
  ['beneficiary', '수취인'],
]

const DropZone = styled(Card)`
  border: 2px dashed ${({ $over, theme }) => ($over ? theme.yellow : '#c9d4dd')};
  background: ${({ $over, theme }) => ($over ? '#fffaf0' : theme.bg)};
  text-align: center;
  padding: 34px 20px;
  color: ${({ theme }) => theme.textMuted};
  b { color: ${({ theme }) => theme.navy}; }
`

const OverallCard = styled(Card)`
  display: flex;
  align-items: center;
  gap: 14px;
  border-left: 6px solid ${({ $color }) => $color};
  font-size: 15px;
  strong { font-size: 19px; color: ${({ theme }) => theme.navy}; }
`

const CheckCard = styled(Card)`
  display: grid;
  grid-template-columns: 28px 110px 1fr;
  gap: 10px;
  align-items: start;
  padding: 14px 18px;
  b { color: ${({ $color }) => $color}; }
  small { color: ${({ theme }) => theme.textMuted}; display: block; margin-top: 4px; }
`

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  td { padding: 8px 10px; border-bottom: 1px solid #edf1f5; }
  td:first-child { color: ${({ theme }) => theme.textMuted}; width: 130px; }
`

export default function DocCheck() {
  const { docResult, setDocResult } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [over, setOver] = useState(false)
  const fileInput = useRef(null)

  const run = async (fn) => {
    setError(null)
    setLoading(true)
    try {
      setDocResult(await fn())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const uploadFile = (file) => {
    if (!file) return
    run(() => postFile('/doc-check', file))
  }

  const loadSample = (name) => run(() => postJson(`/doc-check/sample/${name}`, {}))

  const overall = docResult && STATUS[docResult.overall]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <DropZone
        $over={over}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          uploadFile(e.dataTransfer.files[0])
        }}
        onClick={() => fileInput.current?.click()}
        style={{ cursor: 'pointer' }}
      >
        <b>PI(견적송장)를 끌어다 놓거나 클릭해서 업로드하세요</b>
        <div style={{ marginTop: 6, fontSize: 13 }}>PDF · TXT 지원 (이미지 OCR은 iOS 앱에서)</div>
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.txt"
          hidden
          onChange={(e) => uploadFile(e.target.files[0])}
        />
      </DropZone>

      <div style={{ display: 'flex', gap: 8 }}>
        <GhostButton onClick={() => loadSample('normal')} disabled={loading}>
          📄 샘플: 정상 PI (중국어)
        </GhostButton>
        <GhostButton onClick={() => loadSample('risky')} disabled={loading}>
          ⚠️ 샘플: 위험 PI (중국어)
        </GhostButton>
      </div>

      {error && <ErrorBox>{error}</ErrorBox>}
      {loading && (
        <Card>
          <Skeleton w="30%" />
          <Skeleton w="100%" h="120px" style={{ marginTop: 12 }} />
        </Card>
      )}

      {!loading && docResult && (
        <>
          <OverallCard $color={overall.color}>
            <span style={{ fontSize: 34 }}>{overall.icon}</span>
            <div>
              <strong>종합 판정: {overall.label}</strong>
              <div style={{ marginTop: 4 }}>{docResult.summary}</div>
              <small style={{ color: '#6B7A89' }}>
                {docResult.label || docResult.filename}
                {docResult.fallback ? ' · 폴백 모드(규칙 점검만)' : ''}
              </small>
            </div>
          </OverallCard>

          <Card>
            <SectionTitle>추출된 핵심 조건</SectionTitle>
            <Table>
              <tbody>
                {FIELD_LABELS.map(([key, label]) => (
                  <tr key={key}>
                    <td>{label}</td>
                    <td>{docResult.extracted[key] ?? <em style={{ color: '#c04' }}>미기재</em>}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <SectionTitle>항목별 신호등</SectionTitle>
            {docResult.checks.map((c) => (
              <CheckCard key={c.item} $color={STATUS[c.status].color}>
                <span style={{ fontSize: 20 }}>{STATUS[c.status].icon}</span>
                <b>{c.item}</b>
                <div>
                  {c.finding}
                  <small>근거: {c.basis}</small>
                </div>
              </CheckCard>
            ))}
          </div>
          <NoticeBox>
            자동 점검은 참고용이에요. 큰 금액을 송금하기 전에는 반드시 은행·관세사와 함께 확인하세요.
          </NoticeBox>
        </>
      )}
    </div>
  )
}
