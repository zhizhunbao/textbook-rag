'use client'

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'

/**
 * Auth Provider — Payload 官方 ecommerce 模板模式
 * 通过 /api/users/me REST 端点获取当前用户
 * 提供 login / logout / user 状态
 */

export interface AuthUser {
  id: number
  email: string
  displayName?: string | null
  role: 'admin' | 'editor' | 'reader'
  isOnboarded?: boolean
  selectedPersona?: { id: number; name: string; slug: string; icon?: string } | number | null
}

type Login = (args: { email: string; password: string }) => Promise<AuthUser>
type Logout = () => Promise<void>

type AuthContext = {
  login: Login
  logout: Logout
  setUser: (user: AuthUser | null) => void
  status: 'loggedIn' | 'loggedOut' | undefined
  user?: AuthUser | null
}

const Context = createContext({} as AuthContext)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>()
  const [status, setStatus] = useState<'loggedIn' | 'loggedOut' | undefined>()

  const login = useCallback<Login>(async (args) => {
    try {
      const res = await fetch('/api/users/login', {
        body: JSON.stringify({
          email: args.email,
          password: args.password,
        }),
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      })

      if (res.ok) {
        const { errors, user } = await res.json()
        if (errors) throw new Error(errors[0].message)
        setUser(user)
        setStatus('loggedIn')
        return user
      }

      throw new Error('Invalid login')
    } catch (e) {
      throw new Error('An error occurred while attempting to login.')
    }
  }, [])

  const logout = useCallback<Logout>(async () => {
    try {
      const res = await fetch('/api/users/logout', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      })

      if (res.ok) {
        setUser(null)
        setStatus('loggedOut')
      } else {
        throw new Error('An error occurred while attempting to logout.')
      }
    } catch (e) {
      throw new Error('An error occurred while attempting to logout.')
    }
  }, [])

  // On mount: fetch current user via Payload REST endpoint
  useEffect(() => {
    const fetchMe = async () => {
      try {
        const res = await fetch('/api/users/me', {
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          method: 'GET',
        })

        if (res.ok) {
          const { user: meUser } = await res.json()
          setUser(meUser || null)
          setStatus(meUser ? 'loggedIn' : 'loggedOut')
        } else {
          setUser(null)
          setStatus('loggedOut')
        }
      } catch (e) {
        setUser(null)
        setStatus('loggedOut')
      }
    }

    void fetchMe()
  }, [])

  return (
    <Context.Provider
      value={{
        login,
        logout,
        setUser,
        status,
        user,
      }}
    >
      {children}
    </Context.Provider>
  )
}

type UseAuth = () => AuthContext

export const useAuth: UseAuth = () => useContext(Context)
