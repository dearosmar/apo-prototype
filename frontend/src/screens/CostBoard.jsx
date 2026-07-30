import { useState } from 'react'
import styled, { useTheme } from 'styled-components'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LabelList, ResponsiveContainer } from 'recharts'
import { postJson } from '../api'
import { useAppStore } from '../store'
import { Card, PrimaryButton, GhostButton, ErrorBox, NoticeBox, Skeleton, SectionTitle } from '../components/common'

const PRESET = {
  description: '봉제 인형',
  quantity: 500,
  unit_price: 12,
  currency: 'CNY',
  freight_krw: 300000,
  target_price_krw: 15000,
}

const Grid = styled.div`
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  align-items: start;
  @media (max-width: 860px) { grid-template-columns: 1fr; }
`

const Form = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: 10px;
  label { font-size: 13px; color: ${({ theme }) => theme.textMuted}; }
  input, select {
    width: 100%;
    border: 1px solid #d7dee5;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 15px;
  }
`

const SummaryRow = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
`

const Stat = styled(Card)`
  text-align: center;
  b { display: block; font-size: 22px; color: ${({ theme }) => theme.navy}; margin-top: 6px; }
  span { font-size: 13px; color: ${({ theme }) => theme.textMuted}; }
`

const HsCard = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: 8px;
`

const HsRow = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  code {
    background: ${({ theme }) => theme.navy};
    color: white;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
  }
  em { font-style: normal; color: ${({ theme }) => theme.textMuted}; font-size: 13px; }
`

const ConfBar = styled.div`
  width: 90px;
  height: 8px;
  background: #e4e9ee;
  border-radius: 999px;
  overflow: hidden;
  div { height: 100%; width: ${({ $v }) => $v * 100}%; background: ${({ theme }) => theme.yellow}; }
`

const won = (v) => Math.round(v).toLocaleString('ko-KR') + '원'
const pct = (v) => (v * 100).toFixed(1) + '%'

function Field({ label, ...props }) {
  return (
    <div>
      <label>{label}</label>
      <input {...props} />
    </div>
  )
}

export default function CostBoard() {
  const { costResult, setCostResult } = useAppStore()
  const [form, setForm] = useState(PRESET)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const theme = useTheme()

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (payload) => {
    setError(null)
    setLoading(true)
    try {
      const res = await postJson('/cost', {
        ...payload,
        quantity: Number(payload.quantity),
        unit_price: Number(payload.unit_price),
        freight_krw: Number(payload.freight_krw),
        target_price_krw: payload.target_price_krw ? Number(payload.target_price_krw) : null,
      })
      setCostResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const base = costResult?.scenarios?.[1]
  const chartData = costResult?.scenarios?.map((s) => ({
    name: s.case,
    마진율: s.margin_rate === null ? null : +(s.margin_rate * 100).toFixed(1),
    개당원가: s.unit_cost_krw,
  }))

  return (
    <Grid>
      <Form
        as="form"
        onSubmit={(e) => {
          e.preventDefault()
          submit(form)
        }}
      >
        <SectionTitle>얼마에 팔아야 남을까요?</SectionTitle>
        <Field label="품목 설명" value={form.description} onChange={update('description')} required />
        <Field label="수량 (개)" type="number" min="1" value={form.quantity} onChange={update('quantity')} required />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px', gap: 8 }}>
          <Field label="단가" type="number" step="0.01" min="0.01" value={form.unit_price} onChange={update('unit_price')} required />
          <div>
            <label>통화</label>
            <select value={form.currency} onChange={update('currency')}>
              <option value="CNY">CNY 위안</option>
              <option value="USD">USD 달러</option>
              <option value="JPY">JPY 엔</option>
              <option value="EUR">EUR 유로</option>
            </select>
          </div>
        </div>
        <Field label="운송비 (원)" type="number" min="0" value={form.freight_krw} onChange={update('freight_krw')} />
        <Field label="목표 판매가 (원, 선택)" type="number" min="1" value={form.target_price_krw} onChange={update('target_price_krw')} />
        <PrimaryButton type="submit" disabled={loading}>원가 계산하기</PrimaryButton>
        <GhostButton type="button" onClick={() => { setForm(PRESET); submit(PRESET) }} disabled={loading}>
          🎯 프리셋: 인형 500개 · 개당 12위안
        </GhostButton>
      </Form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {error && <ErrorBox>{error}</ErrorBox>}
        {loading && (
          <Card>
            <Skeleton w="40%" />
            <Skeleton w="100%" h="180px" style={{ marginTop: 12 }} />
          </Card>
        )}
        {!loading && !costResult && (
          <Card>왼쪽에서 조건을 입력하거나 프리셋 버튼을 눌러 보세요. HS코드 추정부터 환율 시나리오 마진까지 한 번에 계산해요.</Card>
        )}
        {!loading && costResult && (
          <>
            <HsCard>
              <SectionTitle>HS코드 후보 (AI 추정)</SectionTitle>
              {costResult.hs.candidates.map((c) => (
                <HsRow key={c.hs_code}>
                  <code>{c.hs_code}</code>
                  <span>{c.name}</span>
                  <ConfBar $v={c.confidence}><div /></ConfBar>
                  <em>{Math.round(c.confidence * 100)}%</em>
                </HsRow>
              ))}
              <HsRow>
                <em>
                  적용 세율 {pct(costResult.applied_tariff.tariff_rate)} — {costResult.applied_tariff.basis}
                </em>
              </HsRow>
              <NoticeBox>{costResult.hs.notice}</NoticeBox>
            </HsCard>

            {base && (
              <SummaryRow>
                <Stat><span>랜디드 코스트 (기준 환율)</span><b>{won(base.landed_cost_krw)}</b></Stat>
                <Stat><span>개당 원가</span><b>{won(base.unit_cost_krw)}</b></Stat>
                <Stat>
                  <span>마진율 {form.target_price_krw ? `(판매가 ${won(Number(form.target_price_krw))})` : ''}</span>
                  <b>{base.margin_rate === null ? '—' : pct(base.margin_rate)}</b>
                </Stat>
              </SummaryRow>
            )}

            <Card>
              <SectionTitle>환율 시나리오별 마진율</SectionTitle>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 13 }} />
                  <YAxis unit="%" tick={{ fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip formatter={(v, name) => (name === '마진율' ? v + '%' : won(v))} />
                  <Bar dataKey="마진율" fill={theme.navy} radius={[6, 6, 0, 0]} barSize={56}>
                    <LabelList dataKey="마진율" position="top" formatter={(v) => v + '%'} style={{ fill: theme.navy, fontWeight: 700 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <NoticeBox>
                환율 출처: {costResult.fx.source} ({costResult.fx.snapshot_date} 기준, {costResult.fx.cur_unit}{' '}
                {costResult.fx.krw_per_unit.toLocaleString('ko-KR')}원)
              </NoticeBox>
            </Card>
          </>
        )}
      </div>
    </Grid>
  )
}
