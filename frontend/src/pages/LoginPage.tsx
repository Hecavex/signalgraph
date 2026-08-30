import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { ApiError } from '../api'
import { useAuth } from '../auth'
import { ErrorBanner, LogoMark } from '../components/Common'

export default function LoginPage() {
  const auth = useAuth()
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('Lead Analyst')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setError('')
    try {
      if (auth.bootstrapRequired) await auth.bootstrap(email, displayName, password)
      else await auth.login(email, password)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Authentication failed')
    } finally {
      setWorking(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="login-brand"><LogoMark size={42} /><strong>SignalGraph</strong></div>
        <div className="story-copy">
          <span className="eyebrow">CONNECTED INTELLIGENCE</span>
          <h1>Make the relationship<br />the starting point.</h1>
          <p>Collect passive signals, preserve provenance, and turn infrastructure overlap into explainable analyst assessments.</p>
          <div className="story-chain">
            <span>collect</span><i /><span>normalize</span><i /><span>correlate</span><i /><span>assess</span>
          </div>
        </div>
        <small>Self-hosted · passive-first · analyst-controlled</small>
      </section>
      <section className="login-panel">
        <form onSubmit={submit}>
          <div className="login-icon"><LockKeyhole size={22} /></div>
          <span className="eyebrow">{auth.bootstrapRequired ? 'FIRST RUN' : 'ANALYST ACCESS'}</span>
          <h2>{auth.bootstrapRequired ? 'Create your administrator' : 'Return to the graph'}</h2>
          <p>{auth.bootstrapRequired ? 'Initialize the first local account for this deployment.' : 'Sign in to your local intelligence workspace.'}</p>
          {error && <ErrorBanner message={error} />}
          {auth.bootstrapRequired && (
            <label>Display name<input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          )}
          <label>Email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<div className="password-field"><input required minLength={12} type={visible ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} /><button type="button" onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
          <button className="primary-button wide" disabled={working}>{working ? 'Authenticating…' : auth.bootstrapRequired ? 'Create administrator' : 'Sign in'}<ArrowRight size={16} /></button>
          <div className="login-assurance"><ShieldCheck size={17} /><span>Credentials stay on your infrastructure.<small>Argon2id password storage · short-lived session token</small></span></div>
        </form>
      </section>
    </main>
  )
}
