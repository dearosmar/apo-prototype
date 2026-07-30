import { useState } from 'react'
import styled from 'styled-components'
import { postJson } from '../api'
import { useAppStore } from '../store'
import { Card, PrimaryButton, GhostButton, ErrorBox, Skeleton } from '../components/common'
import MatchCard from '../components/MatchCard'

const CHIPS = [
  '봉제 인형 KC 인증 필요해?',
  '선금 30%(1,800위안)를 30일 뒤에 보내야 해요. 지금 환전할까요?',
  '해외직구 150달러 넘으면 세금 어떻게 돼?',
  '수입신고는 어떤 순서로 진행돼?',
]

const FX_INTENT = /환전|환율|환헤지|환리스크|송금/
const AMOUNT_RE = /([\d,]+(?:\.\d+)?)\s*(위안|달러|엔|유로|CNY|USD|JPY|EUR)/i
const DAYS_RE = /(\d+)\s*일/
const CURRENCY_MAP = { 위안: 'CNY', 달러: 'USD', 엔: 'JPY', 유로: 'EUR' }

function parseFxParams(question) {
  const amount = question.match(AMOUNT_RE)
  const days = question.match(DAYS_RE)
  const rawCur = amount?.[2]
  return {
    amount_foreign: amount ? Number(amount[1].replaceAll(',', '')) : 1800,
    currency: rawCur ? CURRENCY_MAP[rawCur] || rawCur.toUpperCase() : 'CNY',
    due_days: days ? Number(days[1]) : 30,
    context: question,
  }
}

const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: 14px;
`

const Bubble = styled(Card)`
  max-width: 82%;
  align-self: ${({ $me }) => ($me ? 'flex-end' : 'flex-start')};
  background: ${({ $me, theme }) => ($me ? theme.navy : theme.bg)};
  color: ${({ $me }) => ($me ? 'white' : 'inherit')};
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 15px;
`

const SourceRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
`

const SourceBadge = styled.button`
  background: ${({ $cited, theme }) => ($cited ? theme.yellow : theme.bgSoft)};
  color: ${({ theme }) => theme.navy};
  border: none;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: ${({ $cited }) => ($cited ? 700 : 400)};
`

const Snippet = styled.div`
  margin-top: 10px;
  background: ${({ theme }) => theme.bgSoft};
  border-left: 3px solid ${({ theme }) => theme.yellow};
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  color: ${({ theme }) => theme.textMuted};
`

const InputRow = styled.form`
  display: flex;
  gap: 8px;
  input {
    flex: 1;
    border: 1px solid #d7dee5;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 15px;
  }
`

function sourceLabel(s) {
  let label = s.doc.replaceAll('_', ' ')
  if (s.page) label += ` · p.${s.page}`
  return label
}

function AnswerBubble({ msg }) {
  const [open, setOpen] = useState(null)
  return (
    <Bubble>
      {msg.text}
      {msg.sources?.length > 0 && (
        <>
          <SourceRow>
            {msg.sources.map((s, i) => (
              <SourceBadge
                key={i}
                $cited={s.cited}
                title={s.cited ? '답변에 인용된 출처' : '함께 검색된 자료'}
                onClick={() => setOpen(open === i ? null : i)}
              >
                [{i + 1}] {sourceLabel(s)}
              </SourceBadge>
            ))}
          </SourceRow>
          {open !== null && (
            <Snippet>
              <b>{sourceLabel(msg.sources[open])}</b>
              {msg.sources[open].section ? ` — ${msg.sources[open].section}` : ''}
              <div style={{ marginTop: 6 }}>“{msg.sources[open].snippet}…”</div>
            </Snippet>
          )}
        </>
      )}
    </Bubble>
  )
}

export default function Guide() {
  const { messages, addMessage } = useAppStore()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const send = async (question) => {
    if (!question.trim() || loading) return
    setError(null)
    setInput('')
    addMessage({ role: 'user', text: question })
    if (FX_INTENT.test(question)) {
      addMessage({ role: 'match', initial: parseFxParams(question) })
      return
    }
    setLoading(true)
    try {
      const res = await postJson('/ask', { question })
      addMessage({ role: 'bot', text: res.answer, sources: res.sources, fallback: res.fallback })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Wrap>
      {messages.length === 0 && (
        <Card>
          <b>무엇이든 물어보세요.</b> 관세청·제품안전정보센터 공식 자료에서 근거를 찾아, 출처와
          함께 답해 드려요. 아래 예시를 눌러 시작해 보세요.
        </Card>
      )}
      {messages.map((m, i) => {
        if (m.role === 'user') return <Bubble key={i} $me>{m.text}</Bubble>
        if (m.role === 'match') return <MatchCard key={i} initial={m.initial} />
        return <AnswerBubble key={i} msg={m} />
      })}
      {loading && (
        <Bubble style={{ width: '60%' }}>
          <Skeleton w="90%" />
          <Skeleton w="70%" style={{ marginTop: 8 }} />
          <Skeleton w="80%" style={{ marginTop: 8 }} />
        </Bubble>
      )}
      {error && <ErrorBox>{error} — 잠시 후 다시 시도해 주세요.</ErrorBox>}
      <SourceRow>
        {CHIPS.map((chip) => (
          <GhostButton key={chip} onClick={() => send(chip)} disabled={loading}>
            {chip}
          </GhostButton>
        ))}
      </SourceRow>
      <InputRow
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="예: 봉제 인형 수입할 때 KC 인증이 필요한가요?"
        />
        <PrimaryButton type="submit" disabled={loading || !input.trim()}>
          질문하기
        </PrimaryButton>
      </InputRow>
    </Wrap>
  )
}
