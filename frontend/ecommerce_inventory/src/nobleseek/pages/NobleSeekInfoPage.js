import React from 'react';
import { Container, Typography, Box, Divider } from '@mui/material';
import NewsSeo from '../components/NewsSeo';
import { fetchInfoPage } from '../api';

// Built-in copy: shown while loading AND as fallback when the API is
// unreachable. The desk Pages tab upgrades these without a redeploy.
const DOCS = {
  about: {
    title: 'আমাদের সম্পর্কে',
    intro: 'সত্যের সন্ধানে, সবার আগে।',
    body: `<p><strong>নোবেলসিক (NobleSeek)</strong> একটি বাংলা অনলাইন সংবাদমাধ্যম। দেশ-বিদেশের সর্বশেষ সংবাদ, বিশ্লেষণ ও মতামত আমরা দ্রুত ও নির্ভরযোগ্যভাবে পাঠকের কাছে পৌঁছে দিই।</p><p>আমাদের প্রতিটি প্রতিবেদন যাচাই করা তথ্যের ভিত্তিতে তৈরি। ভুল হলে আমরা স্বচ্ছভাবে সংশোধন করি এবং সংশোধনের নোট প্রতিবেদনে যুক্ত করি। বিজ্ঞাপন ও সম্পাদকীয় বিভাগ সম্পূর্ণ আলাদা — বিজ্ঞাপনদাতারা সংবাদে হস্তক্ষেপ করতে পারেন না।</p>`,
  },
  contact: {
    title: 'যোগাযোগ',
    intro: 'সংবাদ, সংশোধন ও বিজ্ঞাপনের জন্য।',
    body: `<p><strong>নোবেলসিক নিউজরুম</strong><br/>ঢাকা, বাংলাদেশ<br/>ইমেইল: <strong>support@fabrything.com</strong><br/>ফোন: +880 1842-168117</p><p><strong>সংশোধনের জন্য:</strong> খবরের লিংকসহ সঠিক তথ্য পাঠান — ২৪ ঘণ্টার মধ্যে আপডেট করা হয়।</p><p><strong>বিজ্ঞাপন/পার্টনারশিপ:</strong> ইমেইলের বিষয়ে “বিজ্ঞাপন” লিখুন।</p>`,
  },
  privacy: {
    title: 'গোপনীয়তা নীতি',
    intro: 'আপনার তথ্য কীভাবে ব্যবহার হয়।',
    body: `<p>পাঠকসংখ্যা পরিমাপ ও বিজ্ঞাপন পরিবেশনের জন্য আমরা Google AdSense, Google Analytics ও Meta Pixel ব্যবহার করি। এগুলো কুকি সংরক্ষণ করতে পারে। ব্রাউজার থেকে কুকি বন্ধ করলেও সাইট ব্যবহার করা যায়।</p><p>আমরা কখনো ব্যক্তিগত তথ্য বিক্রি করি না। মন্তব্য করতে নাম দিতে হয়; ইমেইল নেওয়া হয় না। তথ্য-সংক্রান্ত অনুরোধে লিখুন: support@fabrything.com।</p>`,
  },
  disclaimer: {
    title: 'ডিসক্লেইমার',
    intro: 'পাঠকের জ্ঞাতার্থে।',
    body: `<p>নোবেলসিকের প্রতিবেদন শুধু তথ্যের উদ্দেশ্যে। আমরা নির্ভরযোগ্য সূত্র থেকে যাচাই করে প্রকাশ করি; চলমান ঘটনার খবর নতুন তথ্য এলে হালনাগাদ করা হয়। ছবির সঙ্গে ক্রেডিট দেওয়া থাকে — কোনো ছবির স্বত্বাধিকারী অপসারণ/ক্রেডিট পরিবর্তন চাইলে যোগাযোগ করুন।</p><p>বিজ্ঞাপন স্পষ্টভাবে চিহ্নিত থাকে এবং তা সম্পাদকীয় সমর্থন বোঝায় না।</p>`,
  },
  ethics: {
    title: 'সম্পাদকীয় নীতি',
    intro: 'যে নীতিতে আমরা সংবাদ প্রকাশ করি।',
    body: `<ul><li>প্রতিটি প্রকাশের আগে মানব সম্পাদকের যাচাই — খসড়া কখনো সরাসরি প্রকাশ হয় না।</li><li>বানোয়াট উদ্ধৃতি নয়, তথ্যহীন চমকপ্রদ শিরোনাম নয়।</li><li>ভুল হলে সংশোধন + প্রতিবেদনের নিচে নোট।</li><li>ক্রেডিটসহ ছবি; গ্রাফিক/আপত্তিকর কনটেন্ট নয়।</li><li>বিজ্ঞাপন ও সম্পাদকীয়র পৃথকীকরণ — বিজ্ঞাপনদাতা কপি অনুমোদন করেন না।</li></ul>`,
  },
};

export default function NobleSeekInfoPage({ page = 'about' }) {
  const fallback = DOCS[page] || DOCS.about;
  const [doc, setDoc] = React.useState(fallback);
  React.useEffect(() => {
    let live = true;
    setDoc(DOCS[page] || DOCS.about);
    fetchInfoPage(page)
      .then((d) => {
        if (live && d && d.body_html) {
          setDoc({ title: d.title, intro: d.intro || '', body: d.body_html });
        }
      })
      .catch(() => {});
    return () => { live = false; };
  }, [page]);
  return (
    <Container maxWidth="md" sx={{ py: { xs: 3, md: 5 } }}>
      <NewsSeo title={doc.title} description={`${doc.title} — নোবেলসিক`} slug={page} />
      <Typography variant="h4" fontWeight={900} className="ns-serif" gutterBottom>{doc.title}</Typography>
      {doc.intro && <Typography variant="subtitle1" color="text.secondary" className="ns-sans" sx={{ mb: 1 }}>{doc.intro}</Typography>}
      <Divider sx={{ mb: 2.5 }} />
      <Box dangerouslySetInnerHTML={{ __html: doc.body }} className="ns-sans" sx={{ '& p': { lineHeight: 1.9, mb: 1.75, color: '#333' }, '& li': { lineHeight: 1.9, mb: 0.75 } }} />
    </Container>
  );
}
