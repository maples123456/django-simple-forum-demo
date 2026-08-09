import { useEffect, useState } from 'react'
import './App.css'

const api = async (url, options = {}) => {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers }
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers })
  if (!response.ok) throw new Error(await response.text() || '请求失败')
  return response.json()
}
const csrf = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ''
const date = (value) => new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })

export default function App() {
  const [boards, setBoards] = useState([]); const [board, setBoard] = useState(null); const [posts, setPosts] = useState([])
  const [post, setPost] = useState(null); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState({ title: '', content: '' }); const [reply, setReply] = useState('')
  const loadBoards = async () => { setLoading(true); try { setBoards((await api('/api/boards/')).boards) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const openBoard = async (id) => { setLoading(true); setError(''); setPost(null); try { const data = await api(`/api/boards/${id}/posts/`); setBoard(data.board); setPosts(data.posts) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const openPost = async (id) => { setLoading(true); setError(''); try { setPost((await api(`/api/posts/${id}/`)).post) } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { loadBoards(); api('/api/csrf/').catch(() => {}) }, [])
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
