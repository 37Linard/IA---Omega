'use client'

import { useCallback, useRef, useState } from 'react'
import { transcribeAudio } from '@/lib/api'

/**
 * Modo de voz contínuo — escuta o mic o tempo todo, dispara sozinho quando
 * ouve a wake word, sem clicar botão nenhum pra cada frase.
 *
 * 100% local de propósito, não usa a Web Speech API do browser (essa manda
 * áudio pro servidor do Google continuamente enquanto ligada — quebraria o
 * "zero dados externos" que o projeto inteiro promete). Reusa o MESMO
 * faster-whisper local que já roda pro botão de microfone hoje
 * (transcribeAudio -> POST /transcribe -> voice.py) — zero dependência nova.
 *
 * Troca-off real, documentado: cada chunk transcrito compete por GPU/CPU com
 * o Ollama. Mitigado com um gate de energia (VAD simples por RMS) — só manda
 * chunk pra transcrever se detectou volume de fala de verdade, silêncio não
 * gasta um único ciclo de whisper.
 *
 * Limitação conhecida: chunks são gravados em sequência (grava 3s, para,
 * transcreve, grava os próximos 3s) — não é uma janela deslizante contínua,
 * então uma wake word falada bem no instante da troca entre chunks pode ser
 * cortada ao meio e não ser reconhecida. Tentar de novo funciona.
 */

const WAKE_WORDS = ['ei agente', 'oi agente', 'e agente', 'ei, agente']
const CHUNK_MS = 3000
const COMMAND_MS = 5000
const SILENCE_RMS_THRESHOLD = 0.015
const MIN_COMMAND_CHARS = 3

export type WakeWordState = 'idle' | 'listening' | 'awaiting_command'

function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim()
}

export function useWakeWord(onCommand: (text: string) => void, isBusy: () => boolean) {
  const [active, setActive] = useState(false)
  const [state, setState] = useState<WakeWordState>('idle')
  const streamRef   = useRef<MediaStream | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const stopRef     = useRef(true)

  const hasSpeech = useCallback((): boolean => {
    const analyser = analyserRef.current
    if (!analyser) return true // sem VAD disponível — fail-open, não trava o loop
    const data = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(data)
    let sumSquares = 0
    for (let i = 0; i < data.length; i++) {
      const norm = (data[i] - 128) / 128
      sumSquares += norm * norm
    }
    const rms = Math.sqrt(sumSquares / data.length)
    return rms > SILENCE_RMS_THRESHOLD
  }, [])

  const recordChunk = useCallback((ms: number): Promise<Blob | null> => {
    return new Promise(resolve => {
      const stream = streamRef.current
      if (!stream) return resolve(null)
      const chunks: BlobPart[] = []
      let mr: MediaRecorder
      try {
        mr = new MediaRecorder(stream)
      } catch {
        return resolve(null)
      }
      mr.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data) }
      mr.onstop = () => resolve(new Blob(chunks, { type: 'audio/webm' }))
      mr.onerror = () => resolve(null)
      mr.start()
      setTimeout(() => { if (mr.state !== 'inactive') mr.stop() }, ms)
    })
  }, [])

  const loop = useCallback(async () => {
    while (!stopRef.current) {
      setState('listening')
      const blob = await recordChunk(CHUNK_MS)
      if (stopRef.current || !blob) continue
      if (!hasSpeech()) continue // silêncio — poupa um ciclo de whisper

      let text = ''
      try {
        const r = await transcribeAudio(blob)
        text = r.text
      } catch {
        continue
      }
      const norm = normalize(text)
      const hit = WAKE_WORDS.find(w => norm.includes(w))
      if (!hit) continue

      const afterWake = norm.slice(norm.indexOf(hit) + hit.length).trim()
      if (afterWake.length > MIN_COMMAND_CHARS) {
        // wake word + comando na mesma respiração
        if (!isBusy()) onCommand(afterWake)
        continue
      }

      // só a wake word — grava o comando separado
      setState('awaiting_command')
      const cmdBlob = await recordChunk(COMMAND_MS)
      if (stopRef.current || !cmdBlob) continue
      try {
        const r = await transcribeAudio(cmdBlob)
        if (r.text.trim().length > MIN_COMMAND_CHARS && !isBusy()) {
          onCommand(r.text.trim())
        }
      } catch {
        // ignora — volta a escutar
      }
    }
  }, [recordChunk, hasSpeech, onCommand, isBusy])

  const start = useCallback(async () => {
    if (!stopRef.current) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 2048
      source.connect(analyser)
      audioCtxRef.current = audioCtx
      analyserRef.current = analyser
      stopRef.current = false
      setActive(true)
      loop()
    } catch {
      // usuário negou permissão de mic ou dispositivo indisponível
      setActive(false)
    }
  }, [loop])

  const stop = useCallback(() => {
    stopRef.current = true
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    audioCtxRef.current?.close()
    audioCtxRef.current = null
    analyserRef.current = null
    setActive(false)
    setState('idle')
  }, [])

  return { active, state, start, stop }
}
