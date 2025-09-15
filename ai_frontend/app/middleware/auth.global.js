// middleware/auth.js
export default defineNuxtRouteMiddleware((to) => {
  const token = process.client ? localStorage.getItem('auth.token') : null

  // если токена нет и это не /login — редиректим
  if (!token && to.path !== '/login') {
    return navigateTo('/login')
  }

  // если токен есть, но юзер пытается открыть /login — можно наоборот отправить на /
  // if (token && to.path === '/login') {
  //   return navigateTo('/')
  // }
})
