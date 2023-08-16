# Posts are a general feture that allows a user to post a comment.  Posts are associated with 
# comments.  Comments are comments on Posts.  It is a discussion board sort of relationship.
# In this site, Posts are associated with Feedback. Posts are posts on Feedback records and serve
# to start a conversation about the feedback record. 

# For a thorough description of this sort of code works, see the Feedback.py file which has
# thorough comments.

from app import app
from flask import render_template, redirect, url_for, session, flash, Markup
from app.classes.data import Post, Comment
from app.classes.forms import PostForm, CommentForm
import datetime as dt
from bson import ObjectId
from flask_login import current_user

@app.route('/posts')
def posts():
 
    posts = Post.objects()
    return render_template("posts.html", posts=posts)

@app.route('/post/<postId>')
def post(postId):

    try:
        announcement = Post.objects.get(pk=postId)
        announceBody = Markup(announcement.body)
    except:
        announcement = None
        announceBody = None

    return render_template('post.html',announcement=announcement, announceBody=announceBody )

@app.route('/newcomment/<postId>', methods=['GET', 'POST'])
def newcomment(postId):
   
    form=CommentForm()
    post=Post.objects.get(pk=postId)
    if form.validate_on_submit():
        newComment = Comment(
            comment=form.comment.data, 
            user=current_user,
            post=post.id
        )
        newComment.save()
        newComment.reload()
        return redirect('/post/'+postId)
    return render_template('commentform.html',post=post, form=form)

@app.route('/deletecomment/<postId>/<commentId>')
def deletecomment(postId, commentId):
 
    deleteComment=Comment.objects.get(pk=commentId)
    if str(deleteComment.user.id) == current_user.id:
        deleteComment.delete()
        flash('Comment deleted.')
    else:
        flash("You can't delete the comment because you don't own it.")
    return redirect('/post/'+postId)

@app.route('/newpost', methods=['GET', 'POST'])
def newpost():
    if not session['isadmin']:
        flash('You must be an administrator to post an annoucement.')
        return redirect('/')

    form = PostForm()

    if form.validate_on_submit():
        newPost = Post(
            subject=form.subject.data, 
            body=form.body.data, 
            user=current_user
        )
        newPost.save()
        newPost.reload()

        return redirect(url_for('post.html',announcement=newPost.id))

    flash('Fill out the form to create a new post')
    return render_template('postform.html', form=form)

@app.route('/editpost/<postId>', methods=['GET', 'POST'])
def editpost(postId):

    editPost = Post.objects.get(pk=postId)
    if editPost.user == current_user:
        form = PostForm()
        if form.validate_on_submit():
            editPost.update(
                subject=form.subject.data,
                body=form.body.data,
                modifydate=dt.datetime.utcnow()
            )
            editPost.reload()
            flash('The post has been edited.')
            return redirect(url_for('post',postId=editPost.id))
        flash('Change the fields below to edit your post')
        form.subject.data = editPost.subject
        form.body.data = editPost.body

        return render_template('postform.html', form=form)
    else:
        flash("You can't edit this post because you are not the author.")
        return redirect(url_for('post', postId=postId))

@app.route('/deletepost/<postId>')
def deletepost(postId):

    deletePost = Post.objects.get(pk=postId)
    if deletePost.user == current_user:
        deletePost.delete()
        flash('Post was deleted')
        posts=Post.objects()
        return render_template('posts.html',posts=posts)
    else:
        flash("You can't delete this post because you are not the author")
        return redirect('/post/'+postId)