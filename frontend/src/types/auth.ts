export interface User {
  id: string
  username: string
}

export interface AuthSession {
  token: string
  user: User
}

export interface AuthCredentials {
  username: string
  password: string
  captcha_id: string
  captcha_answer: string
}

export interface CaptchaChallenge {
  id: string
  image: string
}
