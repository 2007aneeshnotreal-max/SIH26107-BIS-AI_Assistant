import {describe,expect,it} from 'vitest';import {t} from '../lib/i18n'
describe('translations',()=>{it('switches core labels',()=>{expect(t('hi','verify')).toBe('प्रमाणन जाँचें');expect(t('en','verify')).toBe('Verify certification')})})

