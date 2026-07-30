import { useEffect, useState } from 'react'
import styled from 'styled-components'
import { postJson } from '../api'
import { Card, PrimaryButton, ErrorBox, NoticeBox, Skeleton, SectionTitle } from './common'

const LEVEL_COLORS = { 낮음: '#1B9E4B', 중간: '#E8A400', 높음: '#D64545' }

const Wrap = styled(Card)`
  max-width: 82%;
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: 12px;
`

const ParamRow = styled.form`
  display: grid;
  grid-template-columns: 1fr 110px 110px auto;
  gap: 8px;
  align-items: end;
  label { font-size: 12px; color: ${({ theme }) => theme.textMuted}; display: block; }
  input, select {
    width: 100%;
    border: 1px solid #d7dee5;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 14px;
  }
`

const LevelBadge = styled.span`
  display: inline-block;
  background: ${({ $level }) => LEVEL_COLORS[$level] || '#6B7A89'};
  color: white;
  border-radius: 999px;
  padding: 4px 14px;
  font-weight: 700;
  font-size: 14px;
`

const Factor = styled.li`
  font-size: 13px;
  color: ${({ theme }) => theme.textMuted};
  margin-left: 18px;
  line-height: 1.7;
`

const Product = styled.div`
  border: 1px solid #e4e9ee;
  border-left: 4px solid ${({ theme }) => theme.yellow};
  border-radius: 8px;
  padding: 12px 14px;
  b { color: ${({ theme }) => theme.navy}; }
  p { font-size: 14px; margin-top: 6px; line-height: 1.6; }
  small { display: block; margin-top: 6px; color: ${({ theme }) => theme.textMuted}; }
`

export default function MatchCard({ initial }) {
  const [params, setParams] = useState(initial)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async (p) => {
    setError(null)
    setLoading(true)
    try {
      setResult(
        await postJson('/match', {
          currency: p.currency,
          amount_foreign: Number(p.amount_foreign),
          due_days: Number(p.due_days),
          context: p.context,
        }),
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    run(initial)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const update = (key) => (e) => setParams({ ...params, [key]: e.target.value })

  return (
    <Wrap>
      <SectionTitle style={{ marginBottom: 0 }}>💱 환리스크 진단 · KB 상품 매칭</SectionTitle>
      <ParamRow
        onSubmit={(e) => {
          e.preventDefault()
          run(params)
        }}
      >
        <div>
          <label>결제 예정 금액 (외화)</label>
          <input type="number" min="1" value={params.amount_foreign} onChange={update('amount_foreign')} />
        </div>
        <div>
          <label>통화</label>
          <select value={params.currency} onChange={update('currency')}>
            <option value="CNY">CNY</option>
            <option value="USD">USD</option>
            <option value="JPY">JPY</option>
            <option value="EUR">EUR</option>
          </select>
        </div>
        <div>
          <label>결제까지 (일)</label>
          <input type="number" min="0" max="365" value={params.due_days} onChange={update('due_days')} />
        </div>
        <PrimaryButton type="submit" disabled={loading}>재진단</PrimaryButton>
      </ParamRow>

      {error && <ErrorBox>{error}</ErrorBox>}
      {loading && (
        <>
          <Skeleton w="35%" />
          <Skeleton w="100%" h="90px" />
        </>
      )}
      {!loading && result && (
        <>
          <div>
            <LevelBadge $level={result.risk.level}>환리스크 {result.risk.level}</LevelBadge>
            <span style={{ marginLeft: 10, fontSize: 14 }}>
              원화 환산 약 <b>{result.risk.amount_krw.toLocaleString('ko-KR')}원</b>
            </span>
          </div>
          <ul>
            {result.risk.factors.map((f) => (
              <Factor key={f.name}>
                <b>{f.name}</b> — {f.detail}
              </Factor>
            ))}
          </ul>
          {result.recommendations.map((r) => (
            <Product key={r.id}>
              <b>{r.name}</b> <small style={{ display: 'inline' }}>· {r.summary}</small>
              <p>{r.reason}</p>
              <small>⚠️ {r.cautions}</small>
            </Product>
          ))}
          <NoticeBox>{result.notice}</NoticeBox>
        </>
      )}
    </Wrap>
  )
}
