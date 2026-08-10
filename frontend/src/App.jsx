import { useEffect, useState } from 'react'
import './App.css'

const api = async (url, options = {}) => {
  const headers = { 'X-Analytics-Session': sessionId, ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers }
  const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', ...options, headers })
  if (!response.ok) throw new Error(await response.text() || '请求失败')
  return response.json()
}
const csrf = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
const date = (value) => new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
const getId = (storage, key) => { let value = storage.getItem(key); if (!value) { value = crypto.randomUUID(); storage.setItem(key, value) } return value }
const anonymousId = getId(localStorage, 'forum_anonymous_id')
const sessionId = getId(sessionStorage, 'forum_session_id')
const track = (eventName, context = {}) => api('/analytics/api/events/', { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: JSON.stringify({ eventName, anonymousId, sessionId, properties: { path: window.location.pathname }, ...context }) })

function ForumApp() {
  const [boards, setBoards] = useState([]); const [board, setBoard] = useState(null); const [posts, setPosts] = useState([])
  const [post, setPost] = useState(null); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState({ title: '', content: '' }); const [reply, setReply] = useState('')
  const loadBoards = async () => { setLoading(true); try { setBoards((await api('/api/boards/')).boards) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const openBoard = async (id) => { setLoading(true); setError(''); setPost(null); try { const data = await api(`/api/boards/${id}/posts/`); setBoard(data.board); setPosts(data.posts); track('board_view', { boardId: id }).catch(() => {}) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const openPost = async (id) => { setLoading(true); setError(''); try { const data = (await api(`/api/posts/${id}/`)).post; setPost(data); track('post_view', { boardId: data.board.id, postId: id }).catch(() => {}) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { loadBoards(); api('/api/csrf/').then(() => track('page_view')).catch(() => {}) }, [])
  const submitPost = async (event) => { event.preventDefault(); try { const data = await api(`/api/boards/${board.id}/posts/create/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: JSON.stringify(draft) }); setDraft({ title: '', content: '' }); await openPost(data.post.id) } catch (err) { setError(`${err.message} 请先登录。`) } }
  const submitReply = async (event) => { event.preventDefault(); try { await api(`/api/posts/${post.id}/replies/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: JSON.stringify({ content: reply }) }); setReply(''); await openPost(post.id) } catch (err) { setError(`${err.message} 请先登录。`) } }
  const toggleLike = async () => { try { const data = await api(`/api/posts/${post.id}/like/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } }); setPost({ ...post, ...data }) } catch (err) { setError(`${err.message} 请先登录。`) } }
  if (loading && !boards.length) return <main className="shell"><p>正在加载论坛…</p></main>
  return <main className="shell"><header><button className="logo" onClick={() => { setBoard(null); setPost(null) }}>简易论坛</button><a href="/accounts/login/?next=/">登录</a></header>
    {error && <p className="error">{error}</p>}
    {!board && <><section className="hero"><span>REACT + DJANGO</span><h1>用讨论连接想法</h1><p>轻量的演示论坛：进入板块、发表帖子、回复与点赞。</p></section><section className="grid">{boards.map(item => <button className="board" key={item.id} onClick={() => openBoard(item.id)}><h2>{item.name}</h2><p>{item.description || '这里还没有板块简介。'}</p><b>{item.postCount} 篇帖子 →</b></button>)}</section></>}
    {board && !post && <><button className="back" onClick={() => setBoard(null)}>← 所有板块</button><section className="heading"><div><h1>{board.name}</h1><p>{board.description}</p></div></section><section className="posts">{posts.map(item => <button className="post" key={item.id} onClick={() => openPost(item.id)}><div><h2>{item.title}</h2><p>{item.author} · {date(item.createdAt)}</p></div><aside>♡ {item.likeCount}　回复 {item.replyCount}</aside></button>)}</section><form className="composer" onSubmit={submitPost}><h2>发布新帖子</h2><input required value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} placeholder="标题"/><textarea required value={draft.content} onChange={e => setDraft({ ...draft, content: e.target.value })} placeholder="分享你的想法…"/><button>发布</button></form></>}
    {post && <><button className="back" onClick={() => setPost(null)}>← 返回 {post.board.name}</button><article className="detail"><h1>{post.title}</h1><p>{post.author} · {date(post.createdAt)}</p><div className="content">{post.content}</div><button className="like" onClick={toggleLike}>{post.liked ? '♥ 已点赞' : '♡ 点赞'} {post.likeCount}</button></article><section className="replies"><h2>{post.replies.length} 条回复</h2>{post.replies.map(item => <article key={item.id}><b>{item.author}</b><small>{date(item.createdAt)}</small><p>{item.content}</p></article>)}</section><form className="composer" onSubmit={submitReply}><h2>写回复</h2><textarea required value={reply} onChange={e => setReply(e.target.value)} placeholder="参与讨论…"/><button>回复</button></form></>}
  </main>
}

function TrendChart({ data }) {
  const max = Math.max(...data.map(item => item.dau), 1)
  return <div className="trend-chart">{data.map(item => <div className="trend-column" key={item.date} title={`${item.date} · DAU ${item.dau}`}><span>{item.dau || ''}</span><i style={{ height: `${Math.max(item.dau / max * 100, item.dau ? 6 : 1)}%` }}></i><small>{item.date.slice(5)}</small></div>)}</div>
}

function AnalyticsDashboard() {
  const [data, setData] = useState(null); const [days, setDays] = useState(30); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  const load = async (range = days) => { setLoading(true); setError(''); try { setData(await api(`/analytics/api/dashboard/?days=${range}`)) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { api('/api/csrf/').then(() => api('/analytics/api/dashboard/?days=30')).then(setData).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  const changeDays = (value) => { const range = Number(value); setDays(range); load(range) }
  const refresh = async () => { setLoading(true); try { await api('/analytics/api/refresh/', { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: JSON.stringify({ days }) }); await load(days) } catch (err) { setError(err.message); setLoading(false) } }
  const summary = data?.summary || {}
  const cards = [['DAU', summary.dau], ['WAU', summary.wau], ['MAU', summary.mau], ['新增用户', summary.newUsers], ['D1 留存', `${summary.d1Retention || 0}%`, `最近 ${days} 天成熟 Cohort`], ['D7 留存', `${summary.d7Retention || 0}%`, `最近 ${days} 天成熟 Cohort`]]
  return <main className="analytics-shell"><header><div><span>ADMIN ANALYTICS</span><h1>论坛数据指标</h1><p>登录用户活跃、增长、内容互动和新增用户留存。</p></div><a href="/">返回论坛</a></header>
    <div className="toolbar"><select value={days} onChange={event => changeDays(event.target.value)}><option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="90">最近 90 天</option></select><button onClick={refresh} disabled={loading}>{loading ? '生成中…' : '重新生成指标'}</button></div>
    {error && <p className="error">{error}</p>}
    <section className="metric-grid">{cards.map(([label, value, note]) => <article key={label}><span>{label}</span><strong>{value ?? 0}</strong><small>{note || summary.date || '暂无数据'}</small></article>)}</section>
    <section className="analytics-card"><div className="card-heading"><div><h2>DAU 趋势</h2><p>每日产生至少一次有效行为的非管理员登录用户。</p></div></div>{data?.trend?.length ? <TrendChart data={data.trend}/> : <p className="empty-data">点击“重新生成指标”创建第一批汇总数据。</p>}</section>
    <section className="analytics-card"><h2>内容互动趋势</h2><div className="data-table"><table><thead><tr><th>日期</th><th>浏览</th><th>帖子浏览</th><th>新增帖子</th><th>回复</th><th>点赞</th></tr></thead><tbody>{data?.trend?.slice().reverse().map(row => <tr key={row.date}><td>{row.date}</td><td>{row.pageViews}</td><td>{row.postViews}</td><td>{row.posts}</td><td>{row.replies}</td><td>{row.likes}</td></tr>)}</tbody></table></div></section>
    <section className="analytics-card"><h2>新增用户留存 Cohort</h2><p>按注册日期分组，统计第 1、7、30 天再次活跃的用户比例。</p><div className="data-table"><table><thead><tr><th>注册日期</th><th>新增用户</th><th>D1</th><th>D7</th><th>D30</th></tr></thead><tbody>{data?.cohorts?.map(row => <tr key={row.date}><td>{row.date}</td><td>{row.cohortSize}</td><td>{row.d1 == null ? '—' : `${row.d1}%`}</td><td>{row.d7 == null ? '—' : `${row.d7}%`}</td><td>{row.d30 == null ? '—' : `${row.d30}%`}</td></tr>)}</tbody></table></div></section>
  </main>
}

export default function App() {
  return window.location.pathname.startsWith('/analytics') ? <AnalyticsDashboard /> : <ForumApp />
}
