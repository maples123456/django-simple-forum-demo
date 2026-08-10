import { useEffect, useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart,
  Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Scatter,
  ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
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

const chartColors = ['#5b51e8', '#17a673', '#f59e0b', '#ef6a73', '#2f80ed']
const shortDate = value => value?.slice(5)
const number = value => Number(value || 0).toLocaleString('zh-CN')

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map(item => <span key={item.dataKey || item.name} style={{ color: item.color || item.fill }}>{item.name}：{number(item.value)}{String(item.dataKey).startsWith('dau') ? '%' : ''}</span>)}</div>
}

function PostTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return <div className="chart-tooltip"><strong>{item.title}</strong><small>{item.board}</small><span>浏览：{item.views}</span><span>回复：{item.replies}</span><span>点赞：{item.likes}</span></div>
}

function FunnelChart({ rows = [] }) {
  const max = Math.max(...rows.map(row => row.users), 1)
  return <div className="funnel-chart">{rows.map((row, index) => {
    const previous = rows[index - 1]?.users
    const conversion = previous ? Math.round(row.users * 1000 / previous) / 10 : 100
    return <div className="funnel-step" key={row.name}><div className="funnel-label"><b>{row.name}</b><span>{number(row.users)} 人 · {index ? `上一步 ${conversion}%` : '起点'}</span></div><div className="funnel-track"><i style={{ width: `${Math.max(row.users / max * 100, 5)}%`, background: chartColors[index] }}/></div></div>
  })}</div>
}

function RetentionHeatmap({ rows = [] }) {
  const visible = rows.slice(0, 14)
  const color = value => value == null ? '#f2f4f7' : `rgba(91,81,232,${Math.max(.12, Math.min(.9, value / 70))})`
  return <div className="heatmap" role="img" aria-label="新增用户留存 Cohort 热力图">
    <div className="heatmap-row heatmap-head"><span>注册日期</span><b>新增</b><b>D1</b><b>D7</b><b>D30</b></div>
    {visible.map(row => <div className="heatmap-row" key={row.date}><span>{row.date}</span><b className="cohort-size">{row.cohortSize}</b>{[row.d1, row.d7, row.d30].map((value, index) => <i key={index} style={{ background: color(value), color: value > 35 ? '#fff' : '#344054' }}>{value == null ? '—' : `${value}%`}</i>)}</div>)}
  </div>
}

function AnalyticsDashboard() {
  const [data, setData] = useState(null); const [days, setDays] = useState(30); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  const load = async (range = days) => { setLoading(true); setError(''); try { setData(await api(`/analytics/api/dashboard/?days=${range}`)) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { api('/api/csrf/').then(() => api('/analytics/api/dashboard/?days=30')).then(setData).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  const changeDays = (value) => { const range = Number(value); setDays(range); load(range) }
  const refresh = async () => { setLoading(true); try { await api('/analytics/api/refresh/', { method: 'POST', headers: { 'X-CSRFToken': csrf() }, body: JSON.stringify({ days }) }); await load(days) } catch (err) { setError(err.message); setLoading(false) } }
  const summary = data?.summary || {}
  const cards = [
    ['DAU', summary.dau, '昨日有效登录用户'], ['WAU', summary.wau, '滚动 7 日去重'], ['MAU', summary.mau, '滚动 30 日去重'],
    ['窗口活跃用户', summary.activeUsers, `最近 ${days} 日去重`], ['匿名访客', summary.anonymousVisitors, `最近 ${days} 日去重`],
    ['人均帖子浏览', summary.postViewDepth, '帖子浏览 / 活跃用户'], ['创作者率', `${summary.creatorRate || 0}%`, '发帖用户 / 活跃用户'],
    ['讨论参与率', `${summary.discussionRate || 0}%`, '回复用户 / 活跃用户'], ['D1 留存', `${summary.d1Retention || 0}%`, '成熟注册 Cohort'], ['D7 留存', `${summary.d7Retention || 0}%`, '成熟注册 Cohort'],
  ]
  const trend = data?.trend || []
  const segments = (data?.segments || []).filter(item => item.value > 0)
  return <main className="analytics-shell"><header><div><span>ADMIN ANALYTICS</span><h1>论坛业务观测台</h1><p>从用户规模、内容消费、内容生产、互动质量与留存观察社区健康度。</p></div><a href="/">返回论坛</a></header>
    <div className="toolbar"><select value={days} onChange={event => changeDays(event.target.value)}><option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="90">最近 90 天</option></select><button onClick={refresh} disabled={loading}>{loading ? '生成中…' : '重新生成指标'}</button></div>
    {error && <p className="error">{error}</p>}
    <section className="metric-grid">{cards.map(([label, value, note]) => <article key={label}><span>{label}</span><strong>{value ?? 0}</strong><small>{note || summary.date || '暂无数据'}</small></article>)}</section>
    {!trend.length && <section className="analytics-card"><p className="empty-data">点击“重新生成指标”创建第一批汇总数据。</p></section>}
    <section className="chart-grid">
      <article className="analytics-card chart-wide"><div className="card-heading"><div><h2>活跃用户规模</h2><p>DAU、滚动 7 日 WAU 与滚动 30 日 MAU，均按用户去重。</p></div></div><div className="chart-box"><ResponsiveContainer><LineChart data={trend} margin={{ top: 16, right: 18, left: -10, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tickFormatter={shortDate} minTickGap={24}/><YAxis/><Tooltip content={<ChartTooltip/>}/><Legend/><Line name="DAU" type="monotone" dataKey="dau" stroke={chartColors[0]} strokeWidth={3} dot={false}/><Line name="WAU" type="monotone" dataKey="wau" stroke={chartColors[1]} strokeWidth={2} dot={false}/><Line name="MAU" type="monotone" dataKey="mau" stroke={chartColors[2]} strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div></article>
      <article className="analytics-card"><h2>使用频率</h2><p>DAU/WAU 与 DAU/MAU 是活跃频率，不是留存率。</p><div className="chart-box"><ResponsiveContainer><LineChart data={trend} margin={{ top: 16, right: 14, left: -12 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tickFormatter={shortDate} minTickGap={20}/><YAxis unit="%" domain={[0, 'auto']}/><Tooltip content={<ChartTooltip/>}/><Legend/><Line name="DAU/WAU" type="monotone" dataKey="dauWau" stroke={chartColors[0]} strokeWidth={3} dot={false}/><Line name="DAU/MAU" type="monotone" dataKey="dauMau" stroke={chartColors[3]} strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div></article>
      <article className="analytics-card"><h2>登录与匿名访问</h2><p>区分有效登录用户与未登录访客，避免低估全站触达。</p><div className="chart-box"><ResponsiveContainer><AreaChart data={trend} margin={{ top: 16, right: 12, left: -12 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tickFormatter={shortDate} minTickGap={20}/><YAxis/><Tooltip content={<ChartTooltip/>}/><Legend/><Area name="登录活跃" type="monotone" dataKey="dau" stackId="reach" stroke={chartColors[0]} fill="#dcd9ff"/><Area name="匿名访客" type="monotone" dataKey="anonymousVisitors" stackId="reach" stroke={chartColors[1]} fill="#ccefe3"/></AreaChart></ResponsiveContainer></div></article>
      <article className="analytics-card"><h2>内容消费漏斗</h2><p>按窗口内去重用户计算，各阶段允许非严格顺序到达。</p><FunnelChart rows={data?.funnel}/></article>
      <article className="analytics-card"><h2>用户参与层级</h2><p>按窗口内最深行为互斥分组，识别读者、互动者与创作者结构。</p><div className="chart-box"><ResponsiveContainer><PieChart><Pie data={segments} dataKey="value" nameKey="name" innerRadius="52%" outerRadius="78%" paddingAngle={3}>{segments.map((item, index) => <Cell key={item.name} fill={chartColors[index % chartColors.length]}/>)}</Pie><Tooltip formatter={(value, name) => [`${value} 人`, name]}/><Legend/></PieChart></ResponsiveContainer></div></article>
      <article className="analytics-card chart-wide"><h2>内容供给与互动趋势</h2><p>柱形体现发帖、回复、点赞动作量，折线体现帖子消费量。</p><div className="chart-box"><ResponsiveContainer><ComposedChart data={trend} margin={{ top: 16, right: 18, left: -10 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tickFormatter={shortDate} minTickGap={24}/><YAxis yAxisId="left"/><YAxis yAxisId="right" orientation="right"/><Tooltip content={<ChartTooltip/>}/><Legend/><Bar name="发帖" dataKey="posts" stackId="content" fill={chartColors[0]}/><Bar name="回复" dataKey="replies" stackId="content" fill={chartColors[1]}/><Bar name="点赞" dataKey="likes" stackId="content" fill={chartColors[2]} radius={[4,4,0,0]}/><Line name="帖子浏览" yAxisId="right" type="monotone" dataKey="postViews" stroke={chartColors[3]} strokeWidth={3} dot={false}/></ComposedChart></ResponsiveContainer></div></article>
      <article className="analytics-card"><h2>板块贡献</h2><p>横向比较板块的内容消费与互动动作，定位社区重心。</p><div className="chart-box chart-tall"><ResponsiveContainer><BarChart data={data?.boards || []} layout="vertical" margin={{ top: 10, right: 12, left: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="name" type="category" width={76}/><Tooltip content={<ChartTooltip/>}/><Legend/><Bar name="浏览" dataKey="views" fill={chartColors[0]} radius={[0,4,4,0]}/><Bar name="回复" dataKey="replies" fill={chartColors[1]}/><Bar name="点赞" dataKey="likes" fill={chartColors[2]}/></BarChart></ResponsiveContainer></div></article>
      <article className="analytics-card"><h2>帖子健康度</h2><p>每个气泡是一篇帖子；越靠右浏览越高，越靠上讨论越深，气泡越大点赞越多。</p><div className="chart-box chart-tall"><ResponsiveContainer><ScatterChart margin={{ top: 16, right: 20, left: -8, bottom: 8 }}><CartesianGrid strokeDasharray="3 3"/><XAxis type="number" dataKey="views" name="浏览"/><YAxis type="number" dataKey="replies" name="回复"/><ZAxis type="number" dataKey="likes" range={[70, 650]} name="点赞"/><Tooltip content={<PostTooltip/>}/><Scatter data={data?.posts || []} fill={chartColors[0]} fillOpacity={.72}/></ScatterChart></ResponsiveContainer></div></article>
      <article className="analytics-card chart-wide"><h2>新增用户留存 Cohort 热力图</h2><p>每行是一个注册日期 Cohort，颜色越深代表 exact-day（指定日）留存越高；灰色表示观察窗口尚未成熟。</p><RetentionHeatmap rows={data?.cohorts}/></article>
    </section>
  </main>
}

export default function App() {
  return window.location.pathname.startsWith('/analytics') ? <AnalyticsDashboard /> : <ForumApp />
}
