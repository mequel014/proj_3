// middleware/auth.js
export default defineNuxtRouteMiddleware((to) => {

  const token = process.client ? localStorage.getItem('auth.token') : null


  const publicRoutes = new Set([
    '/login',
    '/signup',
    '/signup/complete',
    '/auth/complete-signup',
  ])
  // если токена нет и это не /login — редиректим
  // пускаем без токена только на /login и /signup
  if (!token && !publicRoutes.has(to.path)) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  // если токен есть, но юзер пытается открыть /login — можно наоборот отправить на /
  // if (token && to.path === '/login') {
  //   return navigateTo('/')
  // }
})
